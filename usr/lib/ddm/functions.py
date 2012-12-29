#!/usr/bin/env python -u

import os
import sys
import re
import operator
import string
import shutil
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

# General ================================================


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
def strToNumber(string, toInt=False):
    nr = 0
    try:
        if toInt:
            nr = int(string)
        else:
            nr = float(string)
    except ValueError:
        nr = 0
    return nr


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
    log.write('Search for extensions: %s' % str(extensions), 'functions.getImgsFromDir', 'debug')
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
                    log.write('File with extension found: %s' % path, 'functions.getFilesFromDir', 'debug')
                    break
        else:
            path = os.path.join(directoryPath, fle)
            files.append(path)
            log.write('File found: %s' % path, 'functions.getFilesFromDir', 'debug')
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
# If getLatest is set to True, the latest version of the packages is returned rather than the packages for the currently booted kernel.
# includeLatestRegExp is a regular expression that must be part of the package name (in conjuction with getLatest=True).
# excludeLatestRegExp is a regular expression that must NOT be part of the package name (in conjuction with getLatest=True).
def getLinuxHeadersAndImage(getLatest=False, includeLatestRegExp='', excludeLatestRegExp=''):
    returnList = []
    lhList = []
    ec = ExecCmd(log)
    if getLatest:
        lst = ec.run('aptitude search linux-headers', False)
        for item in lst:
            lhMatch = re.search('linux-headers-\d+\.[a-zA-Z0-9-\.]*', item)
            if lhMatch:
                lh = lhMatch.group(0)
                addLh = True
                if includeLatestRegExp != '':
                    inclMatch = re.search(includeLatestRegExp, lh)
                    if not inclMatch:
                        addLh = False
                if excludeLatestRegExp != '':
                    exclMatch = re.search(excludeLatestRegExp, lh)
                    if exclMatch:
                        addLh = False

                # Append to list
                if addLh:
                    lhList.append(lh)
    else:
        # Get the current linux header package
        linHeader = ec.run('echo linux-headers-$(uname -r)', False)
        lhList.append(linHeader[0])

    # Sort the list and add the linux-image package name
    if lhList:
        lhList.sort(reverse=True)
        returnList.append(lhList[0])
        returnList.append('linux-image-' + lhList[0][14:])
    return returnList


# Get the current kernel release
def getKernelRelease():
    ec = ExecCmd(log)
    kernelRelease = ec.run('uname -r')[0]
    return kernelRelease


# Get the system's graphic card
def getGraphicsCards(pciId=None):
    graphicsCard = []
    cmdGraph = 'lspci -nn | grep VGA'
    ec = ExecCmd(log)
    hwGraph = ec.run(cmdGraph, False)
    for line in hwGraph:
        graphMatch = re.search(':\s(.*)\[', line)
        if graphMatch and (pciId is None or pciId.lower() + ':' in line.lower()):
            graphicsCard.append(graphMatch.group(1))
    return graphicsCard


def getGraphicsCardsManufacturerPciId():
    pciId = []
    cmdGraph = 'lspci -nn | grep VGA'
    ec = ExecCmd(log)
    hwGraph = ec.run(cmdGraph, False)
    for line in hwGraph:
        idMatch = re.search('\[(\w*):(\w*)\]', line)
        if idMatch:
            pciId.append([idMatch.group(1), idMatch.group(2)])
    return pciId


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
def getDistribution():
    distribution = ''
    sysInfo = getSystemVersionInfo().lower()
    if 'debian' in sysInfo:
        distribution = 'debian'
    elif 'ubuntu' in sysInfo:
        distribution = 'ubuntu'
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
    desktop = os.environ.get('DESKTOP_SESSION')
    if desktop is None or desktop == 'default':
        # Dirty: KDE_FULL_SESSION does not always exist: also check if kdm exists
        if 'KDE_FULL_SESSION' in os.environ or os.path.isfile('/usr/bin/kdm'):
            desktop = 'kde'
        elif 'GNOME_DESKTOP_SESSION_ID' in os.environ or 'XDG_CURRENT_DESKTOP' in os.environ:
            desktop = 'gnome'
        elif 'MATE_DESKTOP_SESSION_ID' in os.environ:
            desktop = 'mate'
    return desktop


# Get valid screen resolutions
def getResolutions(minRes='', maxRes='', reverseOrder=False, getUvesafbResolutions=False):
    vbeModes = '/sys/bus/platform/drivers/uvesafb/uvesafb.0/vbe_modes'
    cmd = "xrandr | grep '^\s' | cut -d' ' -f4"
    if getUvesafbResolutions and os.path.exists(vbeModes):
        cmd = "cat %s | cut -d'-' -f1" % vbeModes
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
                    log.write('Resolution added: %s' % item, 'functions.getResolutions', 'debug')
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
        cmdChk = 'apt-cache policy %s' % str(packageName)
        ec = ExecCmd(log)
        packageCheck = ec.run(cmdChk, False)

        for line in packageCheck:
            instChk = re.search('installed:.*\d.*', line.lower())
            if not instChk:
                instChk = re.search('installed.*', line.lower())
                if instChk:
                    # Package is not installed
                    log.write('Package not installed: %s' % str(packageName), 'drivers.getPackageStatus', 'debug')
                    status = packageStatus[1]
                    break
            else:
                # Package is installed
                log.write('Package is installed: %s' % str(packageName), 'drivers.getPackageStatus', 'debug')
                status = packageStatus[0]
                break
        # Package is not found: uninstallable
        if not status:
            log.write('Package not found: %s' % str(packageName), 'drivers.getPackageStatus', 'warning')
            status = packageStatus[2]
    except:
        # If something went wrong: assume that package is uninstallable
        log.write('Could not get status info for package: %s' % str(packageName), 'drivers.getPackageStatus', 'error')
        status = packageStatus[2]

    return status


# Check if a package is installed
def isPackageInstalled(packageName):
    isInstalled = False
    cmd = 'dpkg -s %s | grep Status' % packageName
    ec = ExecCmd(log)
    packageList = ec.run(cmd, False)
    if len(packageList) == 1:
        isInstalled = True
    return isInstalled


# List all dependencies of a package
def getPackageDependencies(packageName, reverseDepends=False):
    retList = []
    cmd = 'apt-cache depends %s | grep " Depends:" | sed -e "s/ Depends: //"' % packageName
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
    cmd = 'apt-cache policy %s | grep Installed' % packageName
    if candidate:
        cmd = 'apt-cache policy %s | grep Candidate' % packageName
    ec = ExecCmd(log)
    versionList = ec.run(cmd, False)
    for line in versionList:
        versionObj = re.search(':\s([\d\.:]*)', line.lower())
        if versionObj:
            version = versionObj.group(1)
    return version


# Get the package description (first line)
def getPackageDescription(packageName):
    name = ''
    cmd = 'apt-cache show %s | grep Description[\-a-z]*:' % packageName
    ec = ExecCmd(log)
    nameList = ec.run(cmd, False)
    for line in nameList:
        nameObj = re.search(':\s(.*)', line)
        if nameObj:
            name = nameObj.group(1)
    return name


# Check if system has wireless (not necessarily a wireless connection)
def hasWireless():
    wl = False
    cmd = 'iwconfig | grep "Access Point"'
    ec = ExecCmd(log)
    wlList = ec.run(cmd, False)
    if wlList:
        for line in wlList:
            if 'Access Point' in line:
                wl = True
                break
    return wl


# Check if we're running live
def isRunningLive():
    live = False
    # Debian live mount directory
    dirLive = '/live'
    # Ubuntu live mount directory
    dirUbiquity = '/rofs'
    if os.path.exists(dirLive) or os.path.exists(dirUbiquity):
        live = True
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
