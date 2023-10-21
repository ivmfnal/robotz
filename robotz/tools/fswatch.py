from pythreader import Primitive, synchronized, schedule_task
import os

class FSWatchdog(Primitive):

    def __init__(self, interval=10, name=None):
        Primitive.__init__(self, name=name)
        self.Watches = {}           # path -> (mtime, callback, param)
        schedule_task(self.run, interval=interval)

    def _getmtime(self, path):
        try:
            return os.stat(path).st_mtime
        except FileNotFoundError:
            return None

    @synchronized
    def run(self):
        new_mtimes = {}
        for path, (mtime, callback, param) in self.Watches.items():
            try:
                new_mtime = self._getmtime(path)
            except Exception as e:
                try:    callback(self, path, param, exception=sys.exc_info())
                except: pass
            else:
                if new_mtime != mtime:
                    try:    callback(self, path, param, mtime=new_mtime)
                    except: pass
                    new_mtimes[path] = new_mtime

        for path, (mtime, callback, param) in list(self.Watches.items()):
            if path in new_mtimes:
                self.Watches[path] = (new_mtimes[path], callback, param)

        if new_mtimes:
            self.wakeup()

    @synchronized
    def add(self, path, callback, param=None):
        mtime = self._getmtime(path)
        self.Watches[path] = (mtime, callback, param)
        return mtime

    @synchronized
    def remove(self, path):
        mtime = None
        while path in self.Watches:
            mtime, _, _ = self.Watches.pop(path)
        return mtime

    __delitem__ = remove

    def __iter__(self):
        return ((path, mtime) for path, (mtime, _, _) in self.Watches.items())

    def __len__(self):
        return len(self.Watches)
        
    def __getitem__(self, path):
        mtime, _, _ = self.Watches[path]
        return mtime