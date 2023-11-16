import getpass
import os
import platform
import shutil
import subprocess
import sys
import time

orig_builtins = __builtins__

def check_return_code(pipeline):
    if hasattr(pipeline, 'check_return_code'):
        return pipeline.check_return_code()
    if pipeline.returncode:
        raise subprocess.CalledProcessError(pipeline.returncode, pipeline.args)

class Pipeline:
    def __repr__(self):
        pipeline = self.spawn()
        pipeline.wait()
        check_return_code(pipeline)
        return ''

    def spawn(self, stdin=None, stdout=None, stderr=None):
        "start this pipeline and return a Popen-like object for it"
        raise NotImplementedError()

    def raw_output(self):
        pipeline = self.spawn(stdout=subprocess.PIPE)
        result = pipeline.stdout.read()
        pipeline.wait()
        return result

    def output(self):
        return self.raw_output().decode()

    def lines(self):
        return self.output().splitlines()

    def line(self):
        return self.lines()[0]

    def __or__(self, other):
        return CombinedPipeline(self, other)

class ShellCommandPipeline(Pipeline):
    __slots__ = ['argv', 'env']
    def __init__(self, argv, env=None):
        self.argv = argv
        self.env = env

    def spawn(self, stdin=None, stdout=None, stderr=None):
        if self.env is None:
            env = None
        else:
            env = os.environ.copy()
            env.update(self.env)
        return subprocess.Popen(self.argv, stdin=stdin, stdout=stdout, stderr=stderr, env=env)

    def with_env(self, env=None, **kwargs):
        return ShellCommandPipeline(self.argv, env or kwargs)

class ShellCommand:
    __slots__ = ['path']
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f'ShellCommand({repr(self.path)})'

    def __call__(self, *args, **kwargs):
        argv = [self.path]
        for k in kwargs:
            if len(k) == 1:
                argv.append(f'-{k}{kwargs[k]}')
            else:
                argv.append(f'--{k}={kwargs[k]}')
        argv.extend(str(arg) for arg in args)
        return ShellCommandPipeline(argv)

class RunningCombinedPipeline:
    __slots__ = ['left','right','stdin','stdout','stderr','returncode']
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.stdin = self.left.stdin
        self.stdout = self.right.stdout
        self.stderr = self.right.stderr
        self.returncode = None

    def poll(self):
        if self.returncode is None:
            left = self.left.poll()
            if left is None:
                return None
            right = self.right.poll()
            self.returncode = left or right
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            if timeout is None:
                self.left.wait()
                self.right.wait()
            else:
                start_time = time.time()
                self.left.wait(timeout)
                remaining_timeout = time.time() - start_time
                self.right.wait(max(remaining_timeout, 0))
            return self.poll()
        return self.returncode

    def check_return_code(self):
        check_return_code(self.left)
        check_return_code(self.right)

    # todo: communicate, send_signal, terminate, kill

class CombinedPipeline(Pipeline):
    __slots__ = ['left','right']
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def spawn(self, stdin=None, stdout=None, stderr=None):
        left = self.left.spawn(stdin=stdin, stdout=subprocess.PIPE, stderr=stderr)
        right = self.right.spawn(stdin=left.stdout, stdout=stdout, stderr=stderr)
        return RunningCombinedPipeline(left, right)

    def with_env(self, env=None, **kwargs):
        env = env or kwargs
        return CombinedPipeline(self.left.with_env(env), self.right.with_env(env))

def command(name):
    path = shutil.which(name)
    if path is not None:
        return ShellCommand(path)

class ShellBuiltins(dict):
    def __getattr__(self, attr):
        try:
            try:
                return super().__getitem__(attr)
            except KeyError:
                return getattr(orig_builtins, attr)
        except AttributeError:
            result = command(attr)
            if result is not None:
                return result
        raise AttributeError(f"command not found: {attr}")

    __getitem__ = __getattr__

class ShellPs1:
    def __str__(self):
        return ps1()

def ps1():
    return f"{getpass.getuser()}@{platform.node()}:{os.getcwd()}>>> "

cd = os.chdir

sys.ps1 = ShellPs1()
shell_builtins = ShellBuiltins()
shell_builtins['__import__'] = __import__
__builtins__ = shell_builtins

