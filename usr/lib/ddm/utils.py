#! /usr/bin/env python3

import subprocess
import urllib.request
import urllib.error
import re
import threading


def shell_exec_popen(command, kwargs={}):
    print(('Executing:', command))
    return subprocess.Popen(command, shell=True,
                            stdout=subprocess.PIPE, **kwargs)


def shell_exec(command):
    print(('Executing:', command))
    return subprocess.call(command, shell=True)


def getoutput(command):
    #return shell_exec(command).stdout.read().strip()
    try:
        output = subprocess.check_output(command, shell=True).decode('utf-8').strip().split('\n')
    except:
        output = []
    return output


def chroot_exec(command):
    command = command.replace('"', "'").strip()  # FIXME
    return shell_exec('chroot /target/ /bin/sh -c "%s"' % command)


def memoize(func):
    """ Caches expensive function calls.

    Use as:

        c = Cache(lambda arg: function_to_call_if_yet_uncached(arg))
        c('some_arg')  # returns evaluated result
        c('some_arg')  # returns *same* (non-evaluated) result

    or as a decorator:

        @memoize
        def some_expensive_function(args [, ...]):
            [...]

    See also: http://en.wikipedia.org/wiki/Memoization
    """
    class memodict(dict):
        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = func(*key)
            return ret
    return memodict()


def get_config_dict(file, key_value=re.compile(r'^\s*(\w+)\s*=\s*["\']?(.*?)["\']?\s*(#.*)?$')):
    """Returns POSIX config file (key=value, no sections) as dict.
    Assumptions: no multiline values, no value contains '#'. """
    d = {}
    with open(file) as f:
        for line in f:
            try:
                key, value, _ = key_value.match(line).groups()
            except AttributeError:
                continue
            d[key] = value
    return d


# Check for internet connection
def hasInternetConnection(testUrl='http://google.com'):
    try:
        urllib.request.urlopen(testUrl, timeout=1)
        return True
    except urllib.error.URLError:
        pass
    return False


# Check if running in VB
def runningInVirtualBox():
    dmiBIOSVersion = getoutput("dmidecode -t0 | grep 'Version:' | awk -F ': ' '{print $2}'")
    dmiSystemProduct = getoutput("dmidecode -t1 | grep 'Product Name:' | awk -F ': ' '{print $2}'")
    dmiBoardProduct = getoutput("dmidecode -t2 | grep 'Product Name:' | awk -F ': ' '{print $2}'")
    if dmiBIOSVersion != "VirtualBox" and dmiSystemProduct != "VirtualBox" and dmiBoardProduct != "VirtualBox":
        return False
    return True


# Check if is 64-bit system
def isAmd64():
    machine = getoutput("uname -m")[0]
    if machine == "x86_64":
        return True
    return False


# Check for backports
def get_backports():
    try:
        bp = getoutput("grep backports /etc/apt/sources.list | grep debian | grep -v ^#")[0]
    except:
        bp = ''
    if bp.strip() == "":
        try:
            bp = getoutput("grep backports /etc/apt/sources.list.d/*.list | grep debian | grep -v ^#")[0]
        except:
            bp = ''
    bp = bp.strip()
    return bp


def has_newer_in_backports(package_name):
    bp = get_backports()
    if bp != '':
        try:
            out = getoutput("apt-cache madison %s | grep %s" % (package_name, bp))[0]
            print((">> has_newer_in_backports =  %s" % out))
            if out != '':
                return True
        except:
            return False
    return False


# Convert string to number
def str_to_nr(stringnr, toInt=False):
    nr = 0
    stringnr = stringnr.strip()
    try:
        if toInt:
            nr = int(stringnr)
        else:
            nr = float(stringnr)
    except ValueError:
        nr = 0
    return nr


# Get Debian's version number (float)
def get_debian_version():
    return str_to_nr(getoutput("head -n 1 /etc/debian_version | sed 's/[a-zA-Z]/0/' 2>/dev/null || echo 0")[0])


def get_apt_options():
    apt_options_8 = '--force-yes --assume-yes --quiet -o Dpkg::Options::=--force-confmiss -o Dpkg::Options::=--force-confnew '
    apt_options_9 = '--assume-yes --quiet --allow-downgrades --allow-remove-essential --allow-change-held-packages -o Dpkg::Options::=--force-confmiss -o Dpkg::Options::=--force-confnew'
    deb_version = get_debian_version()
    if deb_version < 9:
        return apt_options_8
    return apt_options_9


def getPackageVersion(package, candidate=False):
    cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Installed:\"'" % package
    if candidate:
        cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Candidate:\"'" % package
    lst = getoutput(cmd)[0].strip().split(' ')
    version = lst[-1]
    if 'none' in version:
        version = ''
    return version


# Class to run commands in a thread and return the output in a queue
class ExecuteThreadedCommands(threading.Thread):

    def __init__(self, commandList, theQueue=None, returnOutput=False):
        super(ExecuteThreadedCommands, self).__init__()
        self.commands = commandList
        self.queue = theQueue
        self.returnOutput = returnOutput

    def run(self):
        if isinstance(self.commands, (list, tuple)):
            for cmd in self.commands:
                self.exec_cmd(cmd)
        else:
            self.exec_cmd(self.commands)

    def exec_cmd(self, cmd):
        if self.returnOutput:
            ret = getoutput(cmd)
        else:
            ret = shell_exec(cmd)
        if self.queue is not None:
            self.queue.put(ret)
