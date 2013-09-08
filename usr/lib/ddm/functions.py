#!/usr/bin/env python -u

import os
import sys
import re
import operator
import string
import shutil
import apt
import pwd
import grp
import commands
import fnmatch
import urllib2
import gettext
from datetime import datetime
from execcmd import ExecCmd
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)

packageStatus = ['installed', 'notinstalled', 'uninstallable']

# Logging object set from parent
log = object

# i18n
gettext.install("ddm", "/usr/share/locale")


# General ================================================

def locate(pattern, root=os.curdir, locateDirsOnly=False):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.'''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        if locateDirsOnly:
            obj = dirs
        else:
            obj = files
        for objname in fnmatch.filter(obj, pattern):
            yield os.path.join(path, objname)

# Get a list with users, home directory, and a list with groups of that user
def getUsers(homeUsers=True):
    users = []
    userGroups = []
    groups = grp.getgrall()
    for p in pwd.getpwall():
        for g in groups:
            for u in g.gr_mem:
                if u == p.pw_name:
                    userGroups.append(g.gr_name)
        if homeUsers:
            if p.pw_uid > 500 and p.pw_uid < 1500:
                users.append([p.pw_name, p.pw_dir, userGroups])
        else:
            users.append([p.pw_name, p.pw_dir, userGroups])
    return users

# Get the login name of the current user
def getUserLoginName():
    p = os.popen('logname','r')
    userName = string.strip(p.readline())
    p.close()
    return userName

def repaintGui():
    # Force repaint: ugly, but gui gets repainted so fast that gtk objects don't show it
    while gtk.events_pending():
        gtk.main_iteration(False)


# Return the type string of a object
def getTypeString(object):
    tpString = ''
    tp = str(type(object))
    matchObj = re.search("'(.*)'", tp)
    if matchObj:
        tpString = matchObj.group(1)
    return tpString


# Convert string to number
def strToNumber(stringnr, toInt=False):
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


# Check if parameter is a number
def isNumeric(n):
        try:
            n = complex(n)
            return True
        except:
            try:
                n = float(n, 0)
                return True
            except:
                try:
                    n = int(n, 0)
                    return True
                except:
                    return False


# Check if parameter is a list
def isList(lst):
    return isinstance(lst, list)


# Check if parameter is a list containing lists
def isListOfLists(lst):
    return len(lst) == len([x for x in lst if isList(x)])


# Sort list on given column
def sortListOnColumn(lst, columsList):
    for col in reversed(columsList):
        lst = sorted(lst, key=operator.itemgetter(col))
    return lst


# Return a list with images from a given path
def getImgsFromDir(directoryPath):
    extensions = ['.png', '.jpg', '.jpeg', '.gif']
    log.write(_("Search for extensions: %(ext)s") % { "ext": str(extensions) }, 'functions.getImgsFromDir', 'debug')
    imgs = getFilesFromDir(directoryPath, False, extensions)
    return imgs


# Return a list with files from a given path
def getFilesFromDir(directoryPath, recursive=False, extensionList=None):
    if recursive:
        filesUnsorted = getFilesAndFoldersRecursively(directoryPath, True, False)
    else:
        filesUnsorted = os.listdir(directoryPath)
    files = []
    for fle in filesUnsorted:
        if extensionList:
            for ext in extensionList:
                if os.path.splitext(fle)[1] == ext:
                    path = os.path.join(directoryPath, fle)
                    files.append(path)
                    log.write(_("File with extension found: %(path)s") % { "path": path }, 'functions.getFilesFromDir', 'debug')
                    break
        else:
            path = os.path.join(directoryPath, fle)
            files.append(path)
            log.write(_("File found: %(path)s") % { "path": path }, 'functions.getFilesFromDir', 'debug')
    return files


# Get files and folders recursively
def getFilesAndFoldersRecursively(directoryPath, files=True, dirs=True):
    paths = []
    if os.path.exists(directoryPath):
        for dirName, dirNames, fileNames in os.walk(directoryPath):
            if dirs:
                for subDirName in dirNames:
                    paths.append(os.path.join(dirName, subDirName + '/'))
            if files:
                for fileName in fileNames:
                    paths.append(os.path.join(dirName, fileName))
    return paths


# Replace a string (or regular expression) in a file
def replaceStringInFile(findStringOrRegExp, replString, filePath):
    if os.path.exists(filePath):
        tmpFile = '%s.tmp' % filePath
        # Get the data
        f = open(filePath)
        data = f.read()
        f.close()
        # Write the temporary file with new data
        tmp = open(tmpFile, "w")
        tmp.write(re.sub(findStringOrRegExp, replString, data))
        tmp.close()
        # Overwrite the original with the temporary file
        shutil.copy(tmpFile, filePath)
        os.remove(tmpFile)


# Create a backup file with date/time
def backupFile(filePath, removeOriginal=False):
    if os.path.exists(filePath):
        bak = filePath + '.{0:%Y%m%d_%H%M}.bak'.format(datetime.now())
        shutil.copy(filePath, bak)
        if removeOriginal:
            os.remove(filePath)


# Check if a file is locked
def isFileLocked(path):
    locked = False
    cmd = 'lsof %s' % path
    ec = ExecCmd(log)
    lsofList = ec.run(cmd, False)
    for line in lsofList:
        if path in line:
            locked = True
            break
    return locked


# Check for string in file
def doesFileContainString(filePath, searchString):
    doesExist = False
    f = open(filePath, 'r')
    cont = f.read()
    f.close()
    if searchString in cont:
        doesExist = True
    return doesExist


# Statusbar =====================================================

def pushMessage(statusbar, message, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.push(context, message)


def popMessage(statusbar, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.pop(context)


# System ========================================================

# Get linux-headers and linux-image package names
# If getLatest is set to True, the latest version of the packages is returned.
# includeLatestRegExp is a regular expression that must be part of the package name (in conjuction with getLatest=True).
# excludeLatestRegExp is a regular expression that must NOT be part of the package name (in conjuction with getLatest=True).
def getKernelPackages(getLatest=False, includeLatestRegExp='', excludeLatestRegExp=''):
    lst = []
    ec = ExecCmd(log)
    if getLatest:
        cmdList = ec.run('apt-get -s dist-upgrade | grep "linux-image" | grep ^Inst', False)
        if not cmdList:
            # Already the latest kernel: get all linux-image packages of the current version
            kernelRelease = getKernelRelease()
            if 'amd64' in kernelRelease:
                cmd = "aptitude search linux-image-%s" % kernelRelease
            else:
                pos = kernelRelease.find('486')
                if pos == 0:
                    pos = kernelRelease.find('686')
                if pos > 0:
                    kernelRelease = kernelRelease[0:pos - 1]
                cmd = "aptitude search linux-image-%s" % kernelRelease

            cmdList = ec.run(cmd, False)

        for item in cmdList:
            if not '-dbg' in item:
                obj = re.search('linux\-image\-[a-z0-9\-\.]*', item)
                if obj:
                    img = obj.group(0)
                    addImg = True
                    if includeLatestRegExp != '':
                        inclObj = re.search(includeLatestRegExp, img)
                        if not inclObj:
                            addImg = False
                    if excludeLatestRegExp != '':
                        exclObj = re.search(excludeLatestRegExp, img)
                        if exclObj:
                            addImg = False

                    # Append to list
                    if addImg:
                        lst.append(img)
                        lst.append(string.replace(img, "image", "headers"))

        if not lst:
            # Get the current linux header package
            cmdList = ec.run('echo linux-image-$(uname -r)', False)
            img = cmdList[0]
            lst.append(img)
            lst.append(string.replace(img, "image", "headers"))
    else:
        # Get the current linux header package
        cmdList = ec.run('echo linux-image-$(uname -r)', False)
        img = cmdList[0]
        lst.append(img)
        lst.append(string.replace(img, "image", "headers"))

    return lst


# Get the current kernel release
def getKernelRelease():
    ec = ExecCmd(log)
    kernelRelease = ec.run('uname -r', False)[0]
    return kernelRelease


# Get the system's video cards
def getVideoCards(pciId=None):
    videoCard = []
    cmdVideo = 'lspci -nn | grep VGA'
    ec = ExecCmd(log)
    hwVideo = ec.run(cmdVideo, False)
    for line in hwVideo:
        videoMatch = re.search(':\s(.*)\[(\w*):(\w*)\]', line)
        if videoMatch and (pciId is None or pciId.lower() + ':' in line.lower()):
            videoCard.append([videoMatch.group(1), videoMatch.group(2), videoMatch.group(3)])
    return videoCard


# Get system version information
def getSystemVersionInfo():
    info = ''
    try:
        ec = ExecCmd(log)
        infoList = ec.run('cat /proc/version', False)
        if infoList:
            info = infoList[0]
    except Exception, detail:
        log.write(detail, 'functions.getSystemVersionInfo', 'error')
    return info


# Get the system's distribution
def getDistribution(returnBaseDistribution=True):
    distribution = ''
    if returnBaseDistribution:
        sysInfo = getSystemVersionInfo().lower()
        if 'debian' in sysInfo:
            distribution = 'debian'
        elif 'ubuntu' in sysInfo:
            distribution = 'ubuntu'
        elif 'arm' in sysInfo:
            distribution = 'arm'
    else:
        if os.path.exists('/etc/issue.net'):
            ec = ExecCmd(log)
            lst = ec.run('cat /etc/issue.net', False)
            if lst:
                distribution = lst[0]
    return distribution


# Get the system's distribution
def getDistributionDescription():
    distribution = ''
    try:
        cmdDist = 'cat /etc/*-release | grep DISTRIB_DESCRIPTION'
        ec = ExecCmd(log)
        dist = ec.run(cmdDist, False)[0]
        distribution = dist[dist.find('=') + 1:]
        distribution = string.replace(distribution, '"', '')
    except Exception, detail:
        log.write(detail, 'functions.getDistributionDescription', 'error')
    return distribution


# Get the system's distribution
def getDistributionReleaseNumber():
    release = 0
    try:
        cmdRel = 'cat /etc/*-release | grep DISTRIB_RELEASE'
        ec = ExecCmd(log)
        relLst = ec.run(cmdRel, False)
        if relLst:
            rel = relLst[0]
            release = rel[rel.find('=') + 1:]
            release = string.replace(release, '"', '')
            release = strToNumber(release)
    except Exception, detail:
        log.write(detail, 'functions.getDistributionReleaseNumber', 'error')
    return release


# Get the system's desktop
def getDesktopEnvironment():
    desktop_environment = 'generic'
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_environment = 'kde'
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        desktop_environment = 'gnome'
    elif os.environ.get('MATE_DESKTOP_SESSION_ID'):
        desktop_environment = 'mate'
    else:
        try:
            info = commands.getoutput('xprop -root _DT_SAVE_MODE')
            if ' = "xfce4"' in info:
                desktop_environment = 'xfce'
        except (OSError, RuntimeError):
            pass
    return desktop_environment


# Get valid screen resolutions
def getResolutions(minRes='', maxRes='', reverseOrder=False, getVesaResolutions=False):
    cmd = None
    cmdList = ['640x480', '800x600', '1024x768', '1280x1024', '1600x1200']

    if getVesaResolutions:
        vbeModes = '/sys/bus/platform/drivers/uvesafb/uvesafb.0/vbe_modes'
        if os.path.exists(vbeModes):
            cmd = "cat %s | cut -d'-' -f1" % vbeModes
        elif isPackageInstalled('v86d') and isPackageInstalled('hwinfo'):
            cmd = "sudo hwinfo --framebuffer | grep '0x0' | cut -d' ' -f5"
    else:
        cmd = "xrandr | grep '^\s' | cut -d' ' -f4"

    if cmd is not None:
        ec = ExecCmd(log)
        cmdList = ec.run(cmd, False)
    # Remove any duplicates from the list
    resList = list(set(cmdList))

    avlRes = []
    avlResTmp = []
    minW = 0
    minH = 0
    maxW = 0
    maxH = 0

    # Split the minimum and maximum resolutions
    if 'x' in minRes:
        minResList = minRes.split('x')
        minW = strToNumber(minResList[0], True)
        minH = strToNumber(minResList[1], True)
    if 'x' in maxRes:
        maxResList = maxRes.split('x')
        maxW = strToNumber(maxResList[0], True)
        maxH = strToNumber(maxResList[1], True)

    # Fill the list with screen resolutions
    for line in resList:
        for item in line.split():
            itemChk = re.search('\d+x\d+', line)
            if itemChk:
                itemList = item.split('x')
                itemW = strToNumber(itemList[0], True)
                itemH = strToNumber(itemList[1], True)
                # Check if it can be added
                if itemW >= minW and itemH >= minH and (maxW == 0 or itemW <= maxW) and (maxH == 0 or itemH <= maxH):
                    log.write(_("Resolution added: %(res)s") % { "res": item }, 'functions.getResolutions', 'debug')
                    avlResTmp.append([itemW, itemH])

    # Sort the list and return as readable resolution strings
    avlResTmp.sort(key=operator.itemgetter(0), reverse=reverseOrder)
    for res in avlResTmp:
        avlRes.append(str(res[0]) + 'x' + str(res[1]))
    return avlRes


# Check the status of a package
def getPackageStatus(packageName):
    status = ''
    try:
        cache = apt.Cache()
        pkg = cache[packageName]
        if pkg.installed is not None:
            # Package is installed
            log.write(_("Package is installed: %(package)s") % { "package": str(packageName) }, 'drivers.getPackageStatus', 'debug')
            status = packageStatus[0]
        elif pkg.candidate is not None:
            # Package is not installed
            log.write(_("Package not installed: %(package)s") % { "package": str(packageName) }, 'drivers.getPackageStatus', 'debug')
            status = packageStatus[1]
        else:
            # Package is not found: uninstallable
            log.write(_("Package not found: %(package)s") % { "package": str(packageName) }, 'drivers.getPackageStatus', 'debug')
            status = packageStatus[2]
    except:
        # If something went wrong: assume that package is uninstallable
        log.write(_("Could not get status info for package: %(package)s") % { "package": str(packageName) }, 'drivers.getPackageStatus', 'debug')
        status = packageStatus[2]

    return status


# Check if a package is installed
def isPackageInstalled(packageName, alsoCheckVersion=True):
    isInstalled = False
    try:
        cmd = 'dpkg-query -l %s | grep ^i' % packageName
        if '*' in packageName:
            cmd = 'aptitude search %s | grep ^i' % packageName
        ec = ExecCmd(log)
        pckList = ec.run(cmd, False)
        for line in pckList:
            matchObj = re.search('([a-z]+)\s+([a-z0-9\-_\.]*)', line)
            if matchObj:
                if matchObj.group(1)[:1] == 'i':
                    if alsoCheckVersion:
                        cache = apt.Cache()
                        pkg = cache[matchObj.group(2)]
                        if pkg.installed.version == pkg.candidate.version:
                            isInstalled = True
                            break
                    else:
                        isInstalled = True
                        break
            if isInstalled:
                break
    except:
        pass
    return isInstalled


# List all dependencies of a package
def getPackageDependencies(packageName, reverseDepends=False):
    retList = []
    try:
        if reverseDepends:
            cmd = 'apt-cache rdepends %s | grep "^ "' % packageName
            ec = ExecCmd(log)
            depList = ec.run(cmd, False)
            if depList:
                for line in depList:
                    if line[0:2] != 'E:':
                        matchObj = re.search('([a-z0-9\-]+)', line)
                        if matchObj:
                            if matchObj.group(1) != '':
                                retList.append(matchObj.group(1))
        else:
            cache = apt.Cache()
            pkg = cache[packageName]
            for basedeps in pkg.installed.dependencies:
                for dep in basedeps:
                    if dep.version != '':
                        retList.append(dep.name)
    except:
        pass
    return retList


# List all packages with a given installed file name
def getPackagesWithFile(fileName):
    packages = []
    if len(fileName) > 0:
        cmd = 'dpkg -S %s' % fileName
        ec = ExecCmd(log)
        packageList = ec.run(cmd, False)
        for package in packageList:
            if '*' not in package:
                packages.append(package[:package.find(':')])
    return packages


# Check if a process is running
def isProcessRunning(processName):
    isProc = False
    cmd = 'ps -C %s' % processName
    ec = ExecCmd(log)
    procList = ec.run(cmd, False)
    if procList:
        if len(procList) > 1:
            isProc = True
    return isProc


# Kill a process by name and return success
def killProcessByName(processName):
    killed = False
    ec = ExecCmd(log)
    lst = ec.run('killall %s' % processName)
    if len(lst) == 0:
        killed = True
    return killed


# Get the package version number
def getPackageVersion(packageName, candidate=False):
    version = ''
    try:
        cache = apt.Cache()
        pkg = cache[packageName]
        if candidate:
            version = pkg.candidate.version
        elif pkg.installed is not None:
            version = pkg.installed.version
    except:
        pass
    return version


# Get the package description
def getPackageDescription(packageName, firstLineOnly=True):
    descr = ''
    try:
        cache = apt.Cache()
        pkg = cache[packageName]
        descr = pkg.installed.description
        if firstLineOnly:
            lines = descr.split('\n')
            if lines:
                descr = lines[0]
    except:
        pass
    return descr


# Check if system has wireless (not necessarily a wireless connection)
def hasWireless():
    wi = getWirelessInterface()
    if wi is not None:
        return True
    else:
        return False


# Get the wireless interface (usually wlan0)
def getWirelessInterface():
    wi = None
    rtsFound = False
    cmd = 'iwconfig'
    ec = ExecCmd(log)
    wiList = ec.run(cmd, False)
    for line in reversed(wiList):
        if not rtsFound:
            reObj = re.search('\bRTS\b', line)
            if reObj:
                rtsFound = True
        else:
            reObj = re.search('^[a-z0-9]+', line)
            if reObj:
                wi = reObj.group(0)
                break
    return wi


# Check if we're running live
def isRunningLive():
    live = False
    liveDirs = ['/live', '/lib/live', '/rofs']
    for ld in liveDirs:
        if os.path.exists(ld):
            live = True
            break
    return live


# Get diverted files
# mustContain is a string that must be found in the diverted list items
def getDivertedFiles(mustContain=None):
    divertedFiles = []
    cmd = 'dpkg-divert --list'
    if mustContain:
        cmd = 'dpkg-divert --list | grep %s | cut -d' ' -f3' % mustContain
    ec = ExecCmd(log)
    divertedFiles = ec.run(cmd, False)
    return divertedFiles

# Check for internet connection
def hasInternetConnection(testUrl='http://google.com'):
    try:
        urllib2.urlopen(testUrl, timeout=1)
        return True
    except urllib2.URLError:
        pass
    return False

# Get default terminal
def getDefaultTerminal():
    terminal = None
    cmd = "update-alternatives --display x-terminal-emulator"
    ec = ExecCmd(log)
    terminalList = ec.run(cmd, False)
    for line in terminalList:
        reObj = re.search("\'(\/.*)\'", line)
        if reObj:
            terminal = reObj.group(1)
    return terminal