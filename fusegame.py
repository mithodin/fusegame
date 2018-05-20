#!/usr/bin/env python3
#fusepy in debian testing, fuse in pip (why though?)
try:
    import fusepy as fuse
except ImportError:
    import fuse
import logging
import os

import utils
import gamescript as gs

from sys import argv, exit
from time import time
from errno import EACCES, ENODATA

class Fusegame(fuse.LoggingMixIn, fuse.Operations):
    'Example memory filesystem. Supports only one level of files.'

    def __init__(self):
        self.root = utils.Folder("/",0o755)
        self.fd = 0

    def access(self, path, mode):
        f = self.root.get_file(path)
        return f.access(mode)

    def chmod(self, path, mode):
        uid,_,_ = fuse.fuse_get_context()
        fh = self.root.get_file(path)
        if uid == 0 or uid == fh.attrs['st_uid']:
            fh.attrs['st_mode'] &= 0o770000
            fh.attrs['st_mode'] |= mode
            return 0
        else:
            return -1

    def chown(self, path, uid, gid):
        fh = self.root.get_file(path)
        if uid == 0 or uid == fh.attrs['st_uid']:
            fh.set_owner(uid, gid)
            return 0
        else:
            return -1

    def create(self, path, mode):
        p = path.split("/")
        name = p[-1]
        parent = self.root.get_parent(path)
        if parent.access(os.W_OK) == 0:
            f = utils.File(name,mode)
            parent.add_child(f)
            self.fd += 1
            parent.trigger(utils.Event.NEW_CHILD)
        else:
            raise fuse.FuseOSError(EACCES)
        return self.fd

    def getattr(self, path, fh=None):
        fh = self.root.get_file(path)
        return fh.attrs.copy()

    def getxattr(self, path, name, position=0):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})
        try:
            return attrs[name]
        except KeyError:
            raise fuse.FuseOSError(ENODATA)

    def listxattr(self, path):
        fh = self.root.get_file(path)
        attrs = fh.attrs.get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        name = path.split("/")[-1]
        parent = self.root.get_parent(path)
        if parent.access(os.W_OK) == 0:
            nf = utils.Folder(name,mode)
            parent.add_child(nf)
            parent.attrs['st_nlink'] += 1
        else:
            raise fuse.FuseOSError(EACCES)

    def open(self, path, flags):
        #permissions?
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        f = self.root.get_file(path)
        if f.access(os.R_OK) == 0:
            return f.read(size,offset)
        else:
            raise fuse.FuseOSError(EACCES)

    def readdir(self, path, fh):
        f = self.root.get_file(path)
        if f.access(os.R_OK) == 0:
            return f.read()
        else:
            raise fuse.FuseOSError(EACCES)

    def readlink(self, path):
        fh = self.root.get_file(path)
        if f.access(os.R_OK) == 0:
            return fh.read()
        else:
            raise fuse.FuseOSError(EACCES)

    def removexattr(self, path, name):
        fh = self.root.get_file(path)
        if fh.access(os.W_OK) == 0:
            attrs = fh.attrs.get('attrs', {})
            try:
                del attrs[name]
            except KeyError:
                raise fuse.FuseOSError(ENODATA)
        else:
            raise fuse.FuseOSError(EACCES)

    def rename(self, old, new):
        fh = self.root.get_file(old)
        if fh.access(os.W_OK) != 0:
            raise fuse.FuseOSError(EACCES)
        parent_old = self.root.get_parent(old)
        if parent_old.access(os.W_OK) != 0:
            raise fuse.FuseOSError(EACCES)
        parent_old.remove_child(fh)
        parent_new = self.root.get_parent(new)
        if parent_new.access(os.W_OK) != 0:
            raise fuse.FuseOSError(EACCES)
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
        f.trigger(utils.Event.FILE_UPDATE)
        return len(data)

    def __getattrs__(self,name):
        print("Hi, {}.".format(name))
        def method(*args):
            print("Someone tried to call {}, which does not exists.".format(name))
        return method

    def hl_add_trigger(self, path, event, action, once=True):
        f = self.root.get_file(path)
        f.add_trigger(event, action, once)

    def hl_create_file(self, path, contents, mode, hidden=False):
        self.create(path,mode)
        f = self.root.get_file(path)
        if hidden:
            f.hide()
        self.write(path,contents.encode(),0,None)
        return f

    def hl_mkdir(self, path, mode, hidden=False):
        self.mkdir(path,mode)
        f = self.root.get_file(path)
        if hidden:
            f.hide()
        return f

if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.basicConfig(level=logging.DEBUG)
    game = Fusegame()
    gs.setup(game)
    fuse_obj = fuse.FUSE(game, argv[1], foreground=True)
