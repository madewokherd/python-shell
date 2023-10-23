import getpass
import os
import shutil
import subprocess
import sys
import time

orig_builtins = __builtins__

class Pipeline:
    def __repr__(self):
        pipeline = self.execute(check=True)
        pipeline.wait()
        return ''

    def execute(stdin=None, stdout=None, stderr=None, check=False):
        "execute this pipeline and return a Popen-like object for it"
        raise NotImplementedError()

    def raw_output(self):
        pipeline = self.execute(stdout=subprocess.PIPE, check=True)
        result = pipeline.stdout.read()
        pipeline.wait()
        return result

    def output(self):
        return self.raw_output().decode()

    def lines(self):
        return self.output().splitlines()

    def __or__(self, other):
        return CombinedPipeline(self, other)

class ShellCommandPipeline(Pipeline):
    __slots__ = ['argv', 'env']
    def __init__(self, argv, env=None):
        self.argv = argv
        self.env = env

    def execute(self, stdin=None, stdout=None, stderr=None, check=False):
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

    # todo: communicate, send_signal, terminate, kill

class CombinedPipeline(Pipeline):
    __slots__ = ['left','right']
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def execute(self, stdin=None, stdout=None, stderr=None, check=False):
        left = self.left.execute(stdin=stdin, stdout=subprocess.PIPE, stderr=stderr, check=check)
        right = self.right.execute(stdin=left.stdout, stdout=stdout, stderr=stderr, check=check)
        return RunningCombinedPipeline(left, right)

    def with_env(self, env=None, **kwargs):
        env = env or kwargs
        return CombinedPipeline(self.left.with_env(env), self.right.with_env(env))

class ShellBuiltins:
    def __getattr__(self, attr):
        try:
            return getattr(orig_builtins, attr)
        except AttributeError:
            return ShellCommand(shutil.which(attr))

    __getitem__ = __getattr__

class ShellPs1:
    def __str__(self):
        return ps1()

def ps1():
    return f"{getpass.getuser()}@{os.uname().nodename}:{os.getcwd()}>>> "

cd = os.chdir

sys.ps1 = ShellPs1()
__builtins__ = ShellBuiltins()

