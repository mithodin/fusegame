#!/usr/bin/env python3
import fuse
import utils
import logging
import os

from sys import argv, exit
from time import time

class Fusegame(fuse.LoggingMixIn, fuse.Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.root = utils.Folder("/",0o755)
        self.fd = 0

    def chmod(self, path, mode):
        print(path)
        fh = self.root.get_file(path)
        fh.attrs['st_mode'] &= 0o770000
        fh.attrs['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        fh = self.root.get_file(path)
        fh.attrs['st_uid'] = uid
        fh.attrs['st_gid'] = gid

    def create(self, path, mode):
        p = path.split("/")
        name = p[-1]
        parent = self.root.get_parent(path)
        f = utils.File(name,mode)
        parent.add_child(f)
        self.fd += 1
        parent.trigger(utils.Event.NEW_CHILD)
        return self.fd

    def getattr(self, path, fh=None):
        fh = self.root.get_file(path)
        return fh.attrs

    def getxattr(self, path, name, position=0):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        name = path.split("/")[-1]
        parent = self.root.get_parent(path)
        nf = utils.Folder(name,mode)
        parent.add_child(nf)
        parent.attrs['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        f = self.root.get_file(path)
        return f.read(size,offset)

    def readdir(self, path, fh):
        f = self.root.get_file(path)
        return f.read()

    def readlink(self, path):
        fh = self.root.get_file(path)
        return fh.read()

    def removexattr(self, path, name):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        fh = self.root.get_file(old)
        parent_old = self.root.get_parent(old)
        parent_old.remove_child(fh)
        parent_new = self.root.get_parent(new)
        fh.name = new.split("/")[-1]
        parent_new.add_child(fh)

    def rmdir(self, path):
        fh = self.root.get_file(path)
        parent = self.root.get_parent(path)
        parent.remove_child(fh)
        parent.attrs['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        name = target.split("/")[-1]
        lnk = utils.SLink(name,source)
        parent = self.root.get_parent(target)
        parent.add_child(lnk)

    def truncate(self, path, length, fh=None):
        f = self.root.get_file(path)
        f.data = f.data[:length]
        f.attrs['st_size'] = length

    def unlink(self, path):
        parent = self.root.get_parent(path)
        fh = self.root.get_file(path)
        parent.remove_child(fh)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        fh = self.root.get_file(path)
        fh.attrs['st_atime'] = atime
        fh.attrs['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        f = self.root.get_file(path)
        f.data = f.data[:offset] + data
        f.attrs['st_size'] = len(f.data)
        return len(data)

    def add_trigger(self, path, event, action, once=True):
        f = self.root.get_file(path)
        f.add_trigger(event, action, once)

    def __getattrs__(self,name):
        print("Hi, {}.".format(name))
        def method(*args):
            print("Someone tried to call {}, which does not exists.".format(name))
        return method

if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.basicConfig(level=logging.DEBUG)
    game = Fusegame()
    game.mkdir("/secret",0o755)
    fa = utils.Trigger.file_available("/secret/answer.txt",game)
    action = utils.Trigger.create_file("/hallo.txt","Hallo Welt\n",game)
    cond = utils.Trigger.condition(fa,action)
    game.add_trigger("/secret",utils.Event.NEW_CHILD,cond)
    fuse_obj = fuse.FUSE(game, argv[1], foreground=True)
