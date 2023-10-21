from .core import PyThread
from .promise import Promise
import sys, os, subprocess
from subprocess import Popen

def to_str(b):
    if isinstance(b, bytes):
        b = b.decode("utf-8")
    return b

def to_bytes(b):
    if isinstance(b, str):
        b = b.encode("utf-8")
    return b

class ShellCommand(PyThread):

    def __init__(self, command, promise_data=None, cwd=None, env=None, input=None, daemon=None, timeout=None, name=None):
        PyThread.__init__(self, daemon=daemon, name=name)
        self.Command = command
        self.CWD = cwd
        self.Env = env
        self.Input = input
        self.Timeout = timeout
        self.TimedOut = False
        self.Promise = Promise(promise_data)
        self.Out = None
        self.Err = None
        self.Returncode = None

    def run(self):
        p = Popen(self.Command, shell=True,
                    stdin=subprocess.DEVNULL if self.Input is None else suprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=self.CWD, env=self.Env)
        try:    
            out, err = p.communicate(self.Input, self.Timeout)
        except subprocess.TimeoutExpired:
            self.TimedOut = True
            p.kill()
            out, err = p.communicate()
            self.Promise.exception(RuntimeError, RuntimeError("time-out"), None)
            raise RuntimeError("time-out")
        self.Out = to_str(out)
        self.Err = to_str(err)
        self.Returncode = p.returncode
        self.Promise.complete((p.returncode, self.Out, self.Err))
        return self.Returncode, self.Out, self.Err

    @staticmethod
    def execute(command, cwd=None, env=None, input=None, timeout=None, daemon=True):
        s = ShellCommand(command, cwd=cwd, env=env, input=input, daemon=daemon, timeout=timeout)
        return s.run()