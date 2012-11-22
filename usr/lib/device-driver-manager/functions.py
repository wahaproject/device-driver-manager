#!/usr/bin/env python -u

import os
import sys
import re
import operator
import string
from execcmd import ExecCmd
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)

avlThemesSearchstr = 'plymouth-themes'
packageStatus = ['installed', 'notinstalled', 'uninstallable']
graphicsCard = None

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
    log.write('Search for extensions: ' + str(extensions), 'functions.getImgsFromDir', 'debug')
    files = os.listdir(directoryPath)
    img = []
    for file in files:
        for ext in extensions:
            if os.path.splitext(file)[1] == ext:
                path = os.path.join(directoryPath, file)
                img.append(path)
                log.write('Image found: ' + path, 'functions.getImgsFromDir', 'debug')
                break
    return img


# TreeView ==============================================

# Clear treeview
def clearTreeView(treeview):
    liststore = treeview.get_model()
    if liststore is not None:
        liststore.clear()
        treeview.set_model(liststore)


# General function to fill a treeview
# Set setCursorWeight to 400 if you don't want bold font
def fillTreeview(treeview, contentList, columnTypesList, columnHideList=[-1], setCursor=0, setCursorWeight=400, firstItemIsColName=False, appendToExisting=False, appendToTop=False):
    # Check if this is a multi-dimensional array
    multiCols = isListOfLists(contentList)
    colNameList = []

    if len(contentList) > 0:
        liststore = treeview.get_model()
        if liststore is None:
            # Dirty but need to dynamically create a list store
            dynListStore = 'gtk.ListStore('
            for i in range(len(columnTypesList)):
                dynListStore += str(columnTypesList[i]) + ', '
            dynListStore += 'int)'
            log.write('Create list store eval string: ' + dynListStore, 'functions.fillTreeview', 'debug')
            liststore = eval(dynListStore)
        else:
            if not appendToExisting:
                # Existing list store: clear all rows
                log.write('Clear existing list store', 'functions.fillTreeview', 'debug')
                liststore.clear()

        # Create list with column names
        if multiCols:
            for i in range(len(contentList[0])):
                if firstItemIsColName:
                    log.write('First item is column name (multi-column list): ' + contentList[0][i], 'functions.fillTreeview', 'debug')
                    colNameList.append(contentList[0][i])
                else:
                    colNameList.append('Column ' + str(i))
        else:
            if firstItemIsColName:
                log.write('First item is column name (single-column list): ' + contentList[0][i], 'functions.fillTreeview', 'debug')
                colNameList.append(contentList[0])
            else:
                colNameList.append('Column 0')

        log.write('Create column names: ' + str(colNameList), 'functions.fillTreeview', 'debug')

        # Add data to the list store
        for i in range(len(contentList)):
            # Skip first row if that is a column name
            skip = False
            if firstItemIsColName and i == 0:
                log.write('First item is column name: skip first item', 'functions.fillTreeview', 'debug')
                skip = True

            if not skip:
                w = 400
                if i == setCursor:
                    w = setCursorWeight
                if multiCols:
                    # Dynamically add data for multi-column list store
                    if appendToTop:
                        dynListStoreAppend = 'liststore.insert(0, ['
                    else:
                        dynListStoreAppend = 'liststore.append( ['
                    for j in range(len(contentList[i])):
                        val = str(contentList[i][j])
                        if str(columnTypesList[j]) == 'str':
                            val = '"' + val + '"'
                        if str(columnTypesList[j]) == 'gtk.gdk.Pixbuf':
                            val = 'gtk.gdk.pixbuf_new_from_file("' + val + '")'
                        dynListStoreAppend += val + ', '
                    dynListStoreAppend += str(w) + '] )'

                    log.write('Add data to list store (single-column list): ' + dynListStoreAppend, 'functions.fillTreeview', 'debug')
                    eval(dynListStoreAppend)
                else:
                    if appendToTop:
                        log.write('Add data to top of list store (single-column list): ' + str(contentList[i]), 'functions.fillTreeview', 'debug')
                        liststore.insert(0, [contentList[i], w])
                    else:
                        log.write('Add data to bottom of list store (single-column list): ' + str(contentList[i]), 'functions.fillTreeview', 'debug')
                        liststore.append([contentList[i], w])

        # Check last visible column
        lastVisCol = -1
        for i in xrange(len(colNameList), 0, -1):
            if i in columnHideList:
                lastVisCol = i - 1
                log.write('Last visible column nr: ' + str(lastVisCol), 'functions.fillTreeview', 'debug')
                break

        # Create columns
        for i in range(len(colNameList)):
            # Check if we have to hide this column
            skip = False
            for colNr in columnHideList:
                if colNr == i:
                    log.write('Hide column nr: ' + str(colNr), 'functions.fillTreeview', 'debug')
                    skip = True

            if not skip:
                # Create a column only if it does not exist
                colFound = ''
                cols = treeview.get_columns()
                for col in cols:
                    if col.get_title() == colNameList[i]:
                        colFound = col.get_title()
                        break

                if colFound == '':
                    # Build renderer and attributes to define the column
                    # Possible attributes for text: text, foreground, background, weight
                    attr = ', text=' + str(i) + ', weight=' + str(len(colNameList))
                    renderer = 'gtk.CellRendererText()'  # an object that renders text into a gtk.TreeView cell
                    if str(columnTypesList[i]) == 'bool':
                        renderer = 'gtk.CellRendererToggle()'  # an object that renders a toggle button into a TreeView cell
                        attr = ', active=' + str(i)
                    if str(columnTypesList[i]) == 'gtk.gdk.Pixbuf':
                        renderer = 'gtk.CellRendererPixbuf()'  # an object that renders a pixbuf into a gtk.TreeView cell
                        attr = ', pixbuf=' + str(i)
                    dynCol = 'gtk.TreeViewColumn("' + str(colNameList[i]) + '", ' + renderer + attr + ')'

                    log.write('Create column: ' + dynCol, 'functions.fillTreeview', 'debug')
                    col = eval(dynCol)

                    # Get the renderer of the column and add type specific properties
                    rend = col.get_cell_renderers()[0]
                    #if str(columnTypesList[i]) == 'str':
                        # TODO: Right align text in column - add parameter to function
                        #rend.set_property('xalign', 1.0)
                    if str(columnTypesList[i]) == 'bool':
                        # If checkbox column, add toggle function
                        log.write('Check box found: add toggle function', 'functions.fillTreeview', 'debug')
                        rend.connect('toggled', tvchk_on_toggle, liststore, i)

                    # Let the last colum fill the treeview
                    if i == lastVisCol:
                        log.write('Last column fills treeview: ' + str(lastVisCol), 'functions.fillTreeview', 'debug')
                        col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

                    # Finally add the column
                    treeview.append_column(col)
                    log.write('Column added: ' + col.get_title(), 'functions.fillTreeview', 'debug')
                else:
                    log.write('Column already exists: ' + colFound, 'functions.fillTreeview', 'debug')

        # Add liststore, set cursor and set the headers
        treeview.set_model(liststore)
        treeview.set_cursor(setCursor)
        treeview.set_headers_visible(firstItemIsColName)
        log.write('Add Liststrore to Treeview', 'functions.fillTreeview', 'debug')

        # Scroll to selected cursor
        selection = treeview.get_selection()
        tm, treeIter = selection.get_selected()
        path = tm.get_path(treeIter)
        treeview.scroll_to_cell(path)
        log.write('Scrolled to selected row: ' + str(setCursor), 'functions.fillTreeview', 'debug')


def tvchk_on_toggle(cell, path, liststore, colNr, *ignore):
    if path is not None:
        it = liststore.get_iter(path)
        liststore[it][colNr] = not liststore[it][colNr]


# Get the selected value in a treeview
def getSelectedValue(treeView, colNr=0):
    # Assume single row selection
    (model, pathlist) = treeView.get_selection().get_selected_rows()
    return model.get_value(model.get_iter(pathlist[0]), colNr)


# Return all the values in a given column
def getColumnValues(treeView, colNr=0):
    cv = []
    model = treeView.get_model()
    itr = model.get_iter_first()
    while itr is not None:
        cv.append(model.get_value(itr, colNr))
        itr = model.iter_next(itr)
    return cv


# Deselect all drivers, except PAE
def treeviewToggleAll(treeView, toggleColNr, toggleValue=False, excludeColNr=-1, excludeValue=''):
    model = treeView.get_model()
    itr = model.get_iter_first()
    while itr is not None:
        if excludeColNr >= 0:
            exclVal = model.get_value(itr, excludeColNr)
            if exclVal != excludeValue:
                model[itr][toggleColNr] = toggleValue
        else:
            model[itr][toggleColNr] = toggleValue
        itr = model.iter_next(itr)


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
        linHeader = ec.run("echo linux-headers-$(uname -r)", False)
        lhList.append(linHeader[0])

    # Sort the list and add the linux-image package name
    if lhList:
        lhList.sort(reverse=True)
        returnList.append(lhList[0])
        returnList.append('linux-image-' + lhList[0][14:])
    return returnList


# Get the system's graphic card
def getGraphicsCard():
    global graphicsCard
    if graphicsCard is None:
        cmdGraph = 'lspci | grep VGA'
        ec = ExecCmd(log)
        hwGraph = ec.run(cmdGraph, False)
        for line in hwGraph:
            graphicsCard = line[line.find(': ') + 2:]
            break
    return graphicsCard


def getGraphicsCardManufacturerPciId():
    pciId = []
    cmdGraph = 'lspci -nn | grep VGA'
    ec = ExecCmd(log)
    hwGraph = ec.run(cmdGraph, False)
    if hwGraph:
        idMatch = re.search('\[(\w*):(\w*)\]', hwGraph[0])
        if idMatch:
            pciId.append(idMatch.group(1))
            pciId.append(idMatch.group(2))
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
def getResolutions(minRes='', maxRes='', reverseOrder=False):
    cmd = 'xrandr'
    ec = ExecCmd(log)
    cmdList = ec.run(cmd, False)
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
    for line in cmdList:
        for item in line.split():
            if item and 'x' in item and len(item) > 2 and not '+' in item and not 'axis' in item and not 'maximum' in item:
                log.write('Resolution found: ' + item, 'functions.getResolutions', 'debug')
                itemList = item.split('x')
                itemW = strToNumber(itemList[0], True)
                itemH = strToNumber(itemList[1], True)
                # Check if it can be added
                if itemW >= minW and itemH >= minH and (maxW == 0 or itemW <= maxW) and (maxH == 0 or itemH <= maxH):
                    log.write('Resolution added: ' + item, 'functions.getResolutions', 'debug')
                    avlResTmp.append([itemW, itemH])

    # Sort the list and return as readable resolution strings
    avlResTmp.sort(key=operator.itemgetter(0), reverse=reverseOrder)
    for res in avlResTmp:
        avlRes.append(str(res[0]) + 'x' + str(res[1]))
    return avlRes


# Get current Plymouth resolution
def getCurrentResolution():
    res = ''
    boot = getBoot()
    path = os.path.join('/etc/default', boot)
    regExp = 'mode_option=(.*)-'

    if os.path.isfile(path):
        grubfile = open(path, 'r')
        text = grubfile.read()
        grubfile.close()
        # Search text for resolution
        matchObj = re.search(regExp, text)
        if matchObj:
            res = matchObj.group(1)
            log.write('Current Plymouth resolution: ' + res, 'functions.getCurrentResolution', 'debug')
    else:
        log.write('Neither grub nor burg found in /etc/default', 'functions.getCurrentResolution', 'error')

    return res


# Get the bootloader
def getBoot():
    grubPath = '/etc/default/grub'
    burgPath = '/etc/default/burg'
    if os.path.isfile(grubPath):  # Grub
        return 'grub'
    elif os.path.isfile(burgPath):  # Burg
        return 'burg'
    else:
        return ''


# Check the status of a package
def getPackageStatus(packageName):
    status = ''
    try:
        cmdChk = 'apt-cache policy ' + str(packageName)
        ec = ExecCmd(log)
        packageCheck = ec.run(cmdChk, False)

        for line in packageCheck:
            instChk = re.search('installed:.*\d.*', line.lower())
            if not instChk:
                instChk = re.search('installed.*', line.lower())
                if instChk:
                    # Package is not installed
                    log.write('Package not installed: ' + str(packageName), 'drivers.getPackageStatus', 'debug')
                    status = packageStatus[1]
                    break
            else:
                # Package is installed
                log.write('Package is installed: ' + str(packageName), 'drivers.getPackageStatus', 'debug')
                status = packageStatus[0]
                break
        # Package is not found: uninstallable
        if not status:
            log.write('Package not found: ' + str(packageName), 'drivers.getPackageStatus', 'warning')
            status = packageStatus[2]
    except:
        # If something went wrong: assume that package is uninstallable
        log.write('Could not get status info for package: ' + str(packageName), 'drivers.getPackageStatus', 'error')
        status = packageStatus[2]

    return status


# Check if a package is installed
def isPackageInstalled(packageName):
    isInstalled = False
    cmd = 'aptitude search ' + packageName + ' | grep ^i'
    ec = ExecCmd(log)
    packageList = ec.run(cmd, False)
    if packageList:
        if len(packageList) > 0:
            isInstalled = True
    return isInstalled


# List all dependencies of a package
def getPackageDependencies(packageName):
    retList = []
    cmd = 'apt-cache depends ' + packageName + ' | grep Depends'
    ec = ExecCmd(log)
    depList = ec.run(cmd, False)
    if depList:
        for line in depList:
            matchObj = re.search(':\s(.*)', line)
            if matchObj:
                retList.append(matchObj.group(1))
    return retList


# Check if a process is running
def isProcessRunning(processName):
    isProc = False
    cmd = 'ps -C ' + processName
    ec = ExecCmd(log)
    procList = ec.run(cmd, False)
    if procList:
        if len(procList) > 1:
            isProc = True
    return isProc


# Get the package version number
def getPackageVersion(packageName):
    version = ''
    cmd = 'apt-cache policy ' + packageName + ' | grep Installed'
    ec = ExecCmd(log)
    versionList = ec.run(cmd, False)

    for line in versionList:
        versionObj = re.search(':\s(.*)', line.lower())
        if versionObj:
            version = versionObj.group(1)
    return version


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


# Plymouth =============================================

# Get a list of installed Plymouth themes
def getInstalledThemes():
    cmd = '/usr/sbin/plymouth-set-default-theme --list'
    ec = ExecCmd(log)
    instThemes = ec.run(cmd, False)
    return instThemes


# Get the currently used Plymouth theme
def getCurrentTheme():
    curTheme = ['']
    if getCurrentResolution() != '':
        cmd = '/usr/sbin/plymouth-set-default-theme'
        ec = ExecCmd(log)
        curTheme = ec.run(cmd, False)
    return curTheme[0]


# Get a list of Plymouth themes in the repositories that can be installed
def getAvailableThemes():
    cmd = 'aptitude search ' + avlThemesSearchstr + ' | grep ^p'
    ec = ExecCmd(log)
    availableThemes = ec.run(cmd)
    avlThemes = []

    for line in availableThemes:
        matchObj = re.search('plymouth-themes-([a-zA-Z0-9-]*)', line)
        if matchObj:
            theme = matchObj.group(1)
            if not 'all' in theme:
                avlThemes.append(theme)

    return avlThemes


def previewPlymouth():
    cmd = "su -c 'plymouthd; plymouth --show-splash ; for ((I=0; I<10; I++)); do plymouth --update=test$I ; sleep 1; done; plymouth quit'"
    log.write('Preview command: ' + cmd, 'drivers.previewPlymouth', 'debug')
    try:
        ec = ExecCmd(log)
        ec.run(cmd, False)
    except Exception, detail:
        log.write(detail, 'drivers.previewPlymouth', 'error')


# Get the package name that can be uninstalled of a given Plymouth theme
def getRemovablePackageName(theme):
    cmd = 'dpkg -S ' + theme + '.plymouth'
    log.write('Search package command: ' + cmd, 'drivers.getRemovablePackageName', 'debug')
    package = ''
    ec = ExecCmd(log)
    packageNames = ec.run(cmd, False)

    for line in packageNames:
        if avlThemesSearchstr in line:
            matchObj = re.search('(^.*):', line)
            if matchObj:
                package = matchObj.group(1)
                break
    log.write('Package found ' + package, 'drivers.getRemovablePackageName', 'debug')
    return package


# Get valid package name of a Plymouth theme (does not have to exist in the repositories)
def getPackageName(theme):
    return avlThemesSearchstr + "-" + theme
