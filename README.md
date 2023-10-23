# python-shell

This is a project that abuses the Python interactive interpreter to make it behave a bit like a shell. It's pretty barebones, but it proves this silliness is possible.

```
meh@Deej:~$ python -i python-shell.py
meh@Deej:/home/meh>>> ls()
python-shell.py

meh@Deej:/home/meh>>> ls('/').lines()
['bin', 'boot', 'dev', 'etc', 'home', 'init', 'lib', 'lib32', 'lib64', 'libx32', 'lost+found', 'media', 'mnt', 'opt', 'proc', 'root', 'run', 'sbin', 'snap', 'srv', 'sys', 'tmp', 'usr', 'var']
meh@Deej:/home/meh>>> (ls('/')|grep('b')).lines()
['bin', 'boot', 'lib', 'lib32', 'lib64', 'libx32', 'sbin']
```
