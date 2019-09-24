import sys
import fabric as fab
import conf


def convert_to_linux_path(path):
    linux_path = path.replace(conf.win_seperator, conf.linux_seperator)
    return linux_path


# def fab_conn():
#     fab.env.user = conf.user
#     fab.env.password = conf.password
#     fab.env.host_string = conf.host


# def test_fab():
#     fab.run("whoami")


def run_python_nohub():
    cmd_launch_ptvsd = "nohup python3 %s --host 0.0.0.0 --port %d --wait %s/%s &>%s &" % (
        conf.ptvsd_path,
        conf.ptvsd_port,
        conf.remoteRoot,
        convert_to_linux_path(conf.target),
        conf.log_file,
    )

    # pty=False可以解决fabric执行完命令退出，nohup不执行的问题。
    with fab.Connection(conf.host, user=conf.user, connect_kwargs={"password": "zrx"}) as c:
        lib_path = "/opt/rh/rh-python35/root/lib64/:/app/oracle/product/11.2.0/client_1/lib/"
        cmd_export = "export LD_LIBRARY_PATH={lib}:$LD_LIBRARY_PATH".format(lib=lib_path)
        with c.prefix(cmd_export):
            c.run("source ~/.bashrc")
            c.run("source ~/.bash_profile")
            c.run("echo $LD_LIBRARY_PATH")
            c.run(cmd_launch_ptvsd, echo=False)


TARGET = "<filename>"
HELP = """Usage: lauch_ptvsd --host <address> [--port <port>][--log <path>]"""


def print_help_and_exit(switch, it):
    print(HELP, file=sys.stderr)
    sys.exit(0)


__version__ = "r_ptvsd.beta.0.01"


def print_version_and_exit(switch, it):
    print(__version__)
    sys.exit(0)


def set_arg(varname, parser=None):
    def action(arg, it):
        value = parser(next(it)) if parser else arg
        setattr(conf, varname, value)

    return action


switches = [
    # Switch                    Placeholder         Action                                  Required
    # ======                    ===========         ======                                  ========
    # Switches that are documented for use by end users.
    (("-?", "-h", "--help"), None, print_help_and_exit, False),
    (("-V", "--version"), None, print_version_and_exit, False),
    ("--host", "<address>", set_arg("host", str), False),
    ("--port", "<port>", set_arg("ptvsd_port", int), False),
    ("--log-dir", "<path>", set_arg("log_file", str), False),
    ("--remoteRoot", "<path>", set_arg("remoteRoot", str), False),
    ("", "<filename>", set_arg("target"), True),
]


def parse(args):
    unseen_switches = list(switches)

    it = iter(args)
    while True:
        try:
            arg = next(it)
        except StopIteration:
            raise ValueError("missing target: " + TARGET)

        switch = arg if arg.startswith("-") else ""
        for i, (sw, placeholder, action, _) in enumerate(unseen_switches):
            if isinstance(sw, str):
                sw = (sw,)
            if switch in sw:
                del unseen_switches[i]
                break
        else:
            raise ValueError("unrecognized switch " + switch)

        try:
            action(arg, it)
        except StopIteration:
            assert placeholder is not None
            raise ValueError("%s: missing %s" % (switch, placeholder))
        except Exception as ex:
            raise ValueError("invalid %s %s: %s" % (switch, placeholder, str(ex)))

        if conf.target is not None:
            break

    for sw, placeholder, _, required in unseen_switches:
        if required:
            if not isinstance(sw, str):
                sw = sw[0]
            message = "missing required %s" % sw
            if placeholder is not None:
                message += " " + placeholder
            raise ValueError(message)

    return it


def parse_argv(argv):
    saved_argv = list(argv)
    try:
        # sys.argv[:] = [argv[0]] + list(parse(argv[1:]))
        sys.argv[:] = [argv[0]] + list(parse(argv[1:]))
    except Exception as ex:
        print(HELP + "\nError: " + str(ex), file=sys.stderr)
        sys.exit(1)

    print("sys.argv after parsing: ", sys.argv)


def main(argv):
    parse_argv(argv)
    # fab_conn()
    # test_fab()
    run_python_nohub()


if __name__ == "__main__":
    main(sys.argv)
