# 抢在官方发布remote之前
最近由于项目用到了linux的共享内存的库，该库又不能在windows上运行，导致我有部分功能无法在本地调试。遂萌发用vscode调试远端服务器代码的想法。
其实我并不知道官方以及在出这个功能。后来跟同时聊天，同事告诉我官方已经快发布了，不过还是在insider版本。我后来也尝试了下insider版本，一方面insider版本毕竟不是日常的开发环境，再打一套的vscode也比较麻烦，一堆的插件；另一方面，官方的解决方案中，安装remote插件之后，其实是会在服务器上自动下载vscode server的，需要服务器联网。很多童鞋的开发环境，其实是对服务器的联网功能是有限制的。

所以还是按照我原有的思路，完善了这个方案，并最终成功（当然，想做的完美还是有许多功能需要添加的）。
我这个方案还是比较简单的，依赖一个vscode插件和一个python包，可能很多童鞋已经在使用了。真是谁用谁知道。


## 1.插件依赖
   - sftp,vscode插件，本地编辑代码自动同步到服务器。
   - fabric，一个很强大的python ssh包。

   ### fabric安装

    ```pip install fabric3```

## 2.服务器上传ptvsd到指定目录
   ptvsd是微软基于开源调试做的部分封装，该项目微软也是开源的，可以直接在官网下载，官网也提供的whl的安装包。
    微软的python插件已经带了该文件，直接copy到远端也是ok的。

    ```例如：路径：
    /home/yzr/ptvsd
    ```
## 3.launch_ptvsd.py与配置conf.py
   将以下两个python文件copy到本地的目录，例如 `D:\project\python\r_ptvsd`。
   这两个文件一个是主程序，主要用于将是nohup调用服务器上，前面上传或者已经安装的ptvsd模块，以vscode当前文件启动远端的debugger server。
   代码如下：

   ### 1. launch_ptvsd.py

    ```
    import sys
    import fabric.api as fab
    import conf


    def convert_to_linux_path(path):
        linux_path = path.replace(conf.win_seperator, conf.linux_seperator)
        return linux_path


    def fab_conn():
        fab.env.user = conf.user
        fab.env.password = conf.password
        fab.env.host_string = conf.host


    def test_fab():
        fab.run('whoami')


    def run_python_nohub():
        cmd_launch_ptvsd = 'nohup python3 %s --host 0.0.0.0 --port %d --wait %s/%s &>%s &' % (
            conf.ptvsd_path, conf.ptvsd_port, conf.remoteRoot,
            convert_to_linux_path(conf.target), conf.log_file)

        # pty=False可以解决fabric执行完命令退出，nohup不执行的问题。
        fab.run(cmd_launch_ptvsd, pty=False)


    TARGET = '<filename>'
    HELP = '''Usage: lauch_ptvsd --host <address> [--port <port>][--log <path>]'''


    def print_help_and_exit(switch, it):
        print(HELP, file=sys.stderr)
        sys.exit(0)


    __version__ = 'r_ptvsd.beta.0.01'


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
        (('-?', '-h', '--help'), None, print_help_and_exit, False),
        (('-V', '--version'), None, print_version_and_exit, False),
        ('--host', '<address>', set_arg('host', str), False),
        ('--port', '<port>', set_arg('ptvsd_port', int), False),
        ('--log-dir', '<path>', set_arg('log_file', str), False),
        ('', '<filename>', set_arg('target'), True),
    ]


    def parse(args):
        unseen_switches = list(switches)

        it = iter(args)
        while True:
            try:
                arg = next(it)
            except StopIteration:
                raise ValueError('missing target: ' + TARGET)

            switch = arg if arg.startswith('-') else ''
            for i, (sw, placeholder, action, _) in enumerate(unseen_switches):
                if isinstance(sw, str):
                    sw = (sw, )
                if switch in sw:
                    del unseen_switches[i]
                    break
            else:
                raise ValueError('unrecognized switch ' + switch)

            try:
                action(arg, it)
            except StopIteration:
                assert placeholder is not None
                raise ValueError('%s: missing %s' % (switch, placeholder))
            except Exception as ex:
                raise ValueError('invalid %s %s: %s' %
                                (switch, placeholder, str(ex)))

            if conf.target is not None:
                break

        for sw, placeholder, _, required in unseen_switches:
            if required:
                if not isinstance(sw, str):
                    sw = sw[0]
                message = 'missing required %s' % sw
                if placeholder is not None:
                    message += ' ' + placeholder
                raise ValueError(message)

        return it


    def parse_argv(argv):
        saved_argv = list(argv)
        try:
            # sys.argv[:] = [argv[0]] + list(parse(argv[1:]))
            sys.argv[:] = [argv[0]] + list(parse(argv[1:]))
        except Exception as ex:
            print(HELP + '\nError: ' + str(ex), file=sys.stderr)
            sys.exit(1)

        print('sys.argv after parsing: ', sys.argv)


    def main(argv):
        parse_argv(argv)
        fab_conn()
        test_fab()
        run_python_nohub()


    if __name__ == "__main__":
        main(sys.argv)

    ```

### 2.conf.py
```
# -*- coding:utf-8 -*-
# Author: yizr

# 调试的日志输出文件 
log_file = 'out.log'

# vscode在windows与linux上使用的路径分割符
win_seperator = '\\'
linux_seperator = '/'

# ssh
host = '127.0.0.1'
ssh_port = 22
user = 'yzr'
password = 'yzr'

# 远端ptvsd以及源码目录
ptvsd_path = '/home/yzr/ptvsd/ptvsd'
remoteRoot = '/home/yzr/myproject'
ptvsd_port = 5678

# 保持为None
target = None

```


## 4.task
   配置vscode的task

```
{
    // See https://go.microsoft.com/fwlink/?LinkId=733558
    // for the documentation about the tasks.json format
    "version": "2.0.0",
    "tasks": [
        {
            "label": "start_remote_ptsvd",
            "type": "shell",
            "command": "python",
            "args": [
                "D:/project/python/r_ptvsd/launch_ptvsd.py",
                "\"${relativeFile}\"",
                "${relativeFile}",
                "--host 127.0.0.1",
                "--port 5678",
                "--remoteRoot /home/yzr/myproject"
            ]
        }
    ]
}
```
也可以设置该任务的快捷建，这样更方便。
直接修改keymapping.json文件或者按ctrl+k ctl+s直接修改

## 5.调试配置
```
{
            "name": "Python: Remote 127",
            "type": "python",
            "request": "attach",
            "port": 5678,
            "host": "127.0.0.1",
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/home/yzr/myproject"
                }
            ]
        },
```
## 6.后记
    1. 本方案目前基本能向调试本地一样调试远端
    2. 依赖的插件也比较少，主要依赖sftp来完成文件同步。
    3. 与官方比较，官方目前只在insider版本支持此插件。我初步测试了下，官方版本应该是    在服务器上安装一个vscode的server。由于我们的server无法联网（相信很多都是这种    情况）,所以这个方案没有深入测试(有兴趣的同学可以尝试下载上传安装)。有独立   server，官方可以隔离远端与本地，包括插件、环境等，应该还是比较强大的。
      我这个方案胜在简单，够用，这就够了。
      - 补充说明：
      网上很多介绍都说，远端的代码，需要再代码中import ptvsd。
      其实不需要。这样就不会因为调试修改代码了。这应该是新版本的ptvsd的改进的地方了。

## 7.后续可以添加的功能
    1. launch_ptvsd.py增加检查环境变量的功能，确保python3在环境变量中。
    2. launch_ptvsd.py增加检查ptvsd包是否存在，并自动上传的功能。

    其实我原本的想法是，在调试的launch.json中增加preLaunchTask参数，来自动启动远端服务器的。可惜碰到bug，vscode的客户端在服务端启动之前就已经发出请求了，然后就卡死在那知道超时，所以给task增加快捷键也是不得已。
    如果哪位大神有解决方案，欢迎留言交流。对整体方案有什么建议想法都欢迎留言交流。
    共同学习进步。

    github:https://github.com/linbirg/r_ptvsd
    