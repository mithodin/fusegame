try:
    import fusepy as fuse
except ImportError:
    import fuse
import os

from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time
from enum import Enum

class Node:
    def __init__(self,name,mode,hidden=False):
        self.triggers = {}
        self.name = name
        self.hidden = hidden
        uid, gid, _ = fuse.fuse_get_context()
        if uid == 0:
            uid = os.getuid()
            gid = os.getgid()
        self.attrs = dict(st_mode=mode, st_uid = uid, st_gid = gid, st_nlink = 1)

    def add_trigger(self,event,action,once=True):
        self.triggers[event] = Trigger(event,action,once)

    def trigger(self,event):
        try:
            self.triggers[event].execute()
        except:
            pass

    def get_file(self,path):
        return self.getfile(path.split("/")[1:])

    def get_parent(self,path):
        p = path.split("/")
        p[-1] = ""
        return self.get_file("/".join(p))

    def getfile(self,path):
        if len(path) == 0:
            return self

    def show(self):
        self.hidden = False

    def hide(self):
        self.hidden = True

    def node_available(path, game):
        try:
            game.getattr(path)
        except fuse.FuseOSError:
            return False
        return True

    def set_owner(self, uid, gid):
        self.attrs['st_uid'] = uid
        self.attrs['st_gid'] = gid

    def access(self, mode):
        uid, gid, _ = fuse.fuse_get_context()
        if uid == 0:
            return 0
        perm = self.attrs['st_mode']
        if mode & perm == mode:
            return 0
        elif gid == self.attrs['st_gid'] and mode <<3 & perm == mode <<3:
            return 0
        elif uid == self.attrs['st_uid'] and mode <<6 & perm == mode <<6:
            return 0
        return -1

class File(Node):
    def __init__(self,name,mode,hidden=False):
        Node.__init__(self,name,S_IFREG | mode,hidden)
        self.data = bytes()
        now = time()
        self.attrs['st_ctime'] = now
        self.attrs['st_size'] = 0
        self.attrs['st_mtime'] = now
        self.attrs['st_atime'] = now

    def read(self,size=None,offset=0):
        if size == None:
            size = self.attrs['st_size']
        return self.data[offset:offset+size]

class SLink(Node):
    def __init__(self,name,target,hidden=False):
        Node.__init__(self,name,S_FILNK | 0o777,hidden)
        self.target = target
        self.attrs['st_size'] = len(target)

    def read(self):
        return self.target

class Folder(Node):
    def __init__(self,name,mode,hidden=False):
        Node.__init__(self,name,S_IFDIR | mode,hidden)
        self.children = {}
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

    def read(self,size=0,offset=0):
        return ['.','..']+[f.name for f in self.children.values() if not f.hidden]

class Trigger:
    def __init__(self,event,action,once=True):
        self.event = event
        self.action = action
        self.once = once

    def execute(self):
        if self.action() and self.once:
            self.action = lambda: None

    def condition(cond,action):
        def ifthen():
            if cond():
                action()
                return True
            else:
                return False
        return ifthen

    def ready_function(func, *args):
        return lambda: func(*args)

class Event(Enum):
    NEW_CHILD = 1
    FILE_UPDATE = 2
