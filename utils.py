import fuse
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

class File:
    def __init__(self,name,mode):
        self.triggers = []
        self.name = name
        self.data = bytes()
        now = time()
        self.attrs = dict(st_mode=(S_IFREG | mode), st_ctime=now, st_size=0,
                               st_mtime=now, st_atime=now, st_nlink=1)

    def add_trigger(event,action,once=True):
        self.triggers.append(Trigger(event,action,once))

    def get_file(self,path):
        return self.getfile(path.split("/")[1:])

    def get_parent(self,path):
        p = path.split("/")
        p[-1] = ""
        return self.get_file("/".join(p))

    def getfile(self,path):
        if len(path) == 0:
            return self

    def trigger(event):
        for t in self.triggers:
            if t.event == event:
                t.execute()

class SLink:
    def __init__(self,name,target):
        self.target = target
        self.name = name
        self.attrs = dict(st_mode=(S_IFLNK | 0o777), st_size=target.attrs['st_size'], st_nlink=1)

    def __getattr__(self, name):
        def method(*args):
            self.target.__getattr__(name)(args)
        return method

class Folder(File):
    def __init__(self,name,mode):
        File.__init__(self,name,mode)
        self.children = {}
        self.attrs['st_mode'] = S_IFDIR | mode
        self.attrs['st_nlink'] = 2

    def getfile(self,path):
        if ( len(path) == 1 and path[0] == "" ) or len(path) == 0:
            return self
        else:
            try:
                return self.children[path[0]].getfile(path[1:])
            except KeyError:
                raise fuse.FuseOSError(ENOENT)

    def add_child(self,ch):
        if self.children.__contains__(ch.name):
            raise KeyError("Object already exists.")
        self.children[ch.name] = ch

    def remove_child(self,ch):
        self.children.pop(ch.name)

class Trigger:
    def __init__(self,event,action,once=True):
        self.event = event
        self.action = action
        self.once = once

    def execute(self):
        if self.action() and self.once:
            self.action = lambda: None
