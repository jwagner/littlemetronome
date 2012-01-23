from distutils.core import setup
import os

def ls_r(dir):
    def do_reduce(a, b):
        files = []
        for f in b[2]:
            files.append(os.path.join(b[0], f))
        a.append((b[0], files))
        return a
    return reduce(do_reduce, os.walk(dir), [])

print ls_r('share')

setup(
        name='littlemetronome',
        version='0.0',
        author = 'Jonas Wagner',
        author_email = 'jonas@29a.ch',
        url = 'http://29a.ch/littlemetronome/',
        scripts=['bin/littlemetronome'],
        data_files = ls_r('share'),
        license = 'GNU GPL v3',
        packages=['littlemetronome']
)

