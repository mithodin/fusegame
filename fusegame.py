#!/usr/bin/env python3
import fuse
import utils
import logging

from sys import argv, exit
from time import time

class Memory(fuse.LoggingMixIn, fuse.Operations):
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
        p = path.split("/")
        name = p[-1]
        parent = self.root.get_parent(path)
        nf = utils.Folder(name,mode)
        parent.attrs['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        fh = self.root.get_file(path)
        return fh.data[offset:offset + size]

    def readdir(self, path, fh):
        fh = self.root.get_file(path)
        return ['.', '..'] + [f.name for f in fh.children.values()]

    def readlink(self, path):
        fh = self.root.get_file(path)
        return fh.data

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
        fh = self.root.get_file(source)
        parent = self.root.get_parent(target)
        name = target.split("/")[-1]
        parent.add_child(utils.SLink(name,fh))

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


if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.basicConfig(level=logging.DEBUG)
    fuse_obj = fuse.FUSE(Memory(), argv[1], foreground=True)
