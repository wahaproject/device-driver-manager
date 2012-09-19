#!/usr/bin/env python -u

import os
import sys
import subprocess
import re
import types
import operator
import string
import gtk
from execcmd import ExecCmd
from config import Config
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)

conf = Config('ddb.conf')
avlThemesSearchstr = 'plymouth-themes'
packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
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


# Convert string to integer
def strToInt(str):
    try:
        i = int(str)
    except ValueError:
        i = 0
    return i

def isList(list):
    return type(list) == types.ListType

def isListOfLists(list):
    return len(list) == len([x for x in list if type(x) == types.ListType])

def sortListOnColumn(list, columsList):
    for col in reversed(columsList):
        list = sorted(list, key=operator.itemgetter(col))
    return list

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
    if liststore != None:
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
        if liststore == None:
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
                break;
        
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
                    renderer = 'gtk.CellRendererText()' #an object that renders text into a gtk.TreeView cell
                    if str(columnTypesList[i]) == 'bool':
                        renderer = 'gtk.CellRendererToggle()' #an object that renders a toggle button into a TreeView cell
                        attr = ', active=' + str(i)
                    if str(columnTypesList[i]) == 'gtk.gdk.Pixbuf':
                        renderer = 'gtk.CellRendererPixbuf()' #an object that renders a pixbuf into a gtk.TreeView cell
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
    (model,pathlist) = treeView.get_selection().get_selected_rows()
    return model.get_value(model.get_iter(pathlist[0]), colNr)

# Return all the values in a given column
def getColumnValues(treeView, colNr=0):
    cv = []
    model = treeView.get_model()
    iter = model.get_iter_first()
    while iter != None:
        cv.append(model.get_value(iter, colNr))
        iter = model.iter_next(iter)
    return cv

# Statusbar =====================================================

def pushMessage(statusbar, message, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.push(context, message)

def popMessage(statusbar, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.pop(context)

# System ========================================================

def getLatestLunuxHeader(includeString='', excludeString=''):
    lhList = []
    ec = ExecCmd(log)
    list = ec.run('apt search linux-headers', False)
    startIndex = 14
    for item in list:
        lhMatch = re.search('linux-headers-\d[a-zA-Z0-9-\.]*', item)
        if lhMatch:
            lh = lhMatch.group(0)
            addLh = True
            if includeString != '':
                inclMatch = re.search(includeString, lh)
                if inclMatch:
                    if excludeString != '':
                        exclMatch = re.search(excludeString, lh)
                        if exclMatch:
                            addLh = False
                else:
                    addLh = False
        
            # Append to list
            if addLh:
                lhList.append(lh)
    lhList.sort(reverse=True)
    return lhList[0]
        

# Get the system's graphic card
def getGraphicsCard():
    global graphicsCard
    if graphicsCard == None:
        cmdGraph = 'lspci | grep VGA'
        ec = ExecCmd(log)
        hwGraph = ec.run(cmdGraph, False)
        for line in hwGraph:
            graphicsCard = line[line.find(': ') + 2:]
            break
    return graphicsCard

# Get the system's distribution
def getDistribution():
    distribution = ''
    try:
        cmdDist = 'cat /etc/*-release | grep DISTRIB_CODENAME'
        ec = ExecCmd(log)
        dist = ec.run(cmdDist, False)[0]
        distribution = dist[dist.find('=') + 1:]
    except Exception, detail:
        log.write(detail, 'functions.getDistribution', 'error')
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

# Get the system's desktop
def getDesktop():
    desktop = ''
    kdm = '/usr/bin/kdm'
    if os.path.isfile(kdm):
        desktop = 'kde'
    else:
        desktop = 'gnome'
    return desktop

# Get valid screen resolutions
def getResolutions(minRes, maxRes):
    cmd = 'xrandr'
    ec = ExecCmd(log)
    cmdList = ec.run(cmd, False)
    avlRes = [] # Available Resolutions

    # Split the minimum and maximum resolutions
    minResList = minRes.split('x')
    maxResList = maxRes.split('x')
    minW = strToInt(minResList[0])
    minH = strToInt(minResList[1])
    maxW = strToInt(maxResList[0])
    maxH = strToInt(maxResList[1])

    # Fill the list with screen resolutions
    for line in cmdList:
        for item in line.split():
            if item and 'x' in item and len(item) > 2 and not '+' in item and not 'axis' in item and not 'maximum' in item:
                log.write('Resolution found: ' + item, 'functions.getResolutions', 'debug')
                itemList = item.split('x')
                itemW = strToInt(itemList[0])
                itemH = strToInt(itemList[1])
                # Check if it can be added
                if itemW >= minW and itemW <= maxW and itemH >= minH and itemH <= maxH:
                    log.write('Resolution added: ' + item, 'functions.getResolutions', 'debug')
                    avlRes.append(item)
    return avlRes

# Get current Plymouth resolution
def getCurrentResolution():
    res = ''
    boot = getBoot()
    path = os.path.join('/etc/default', boot)
    regExp = 'mode_option=(.*)-'
    
    if os.path.isfile(path):
        file = open(path,'r')
        text = file.read()
        file.close()
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
    if os.path.isfile(grubPath): # Grub
        return 'grub'
    elif os.path.isfile(burgPath): # Burg
        return 'burg'
    else:
        return ''
    
# Check the status of a package
def getPackageStatus(packageName):
    try:
        cmdChk = 'apt-cache policy ' + str(packageName)
        status = []
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
    startmatch = '39m-'
    cmd = 'apt search ' + avlThemesSearchstr + ' | grep ^p'
    ec = ExecCmd(log)
    availableThemes = ec.run(cmd, False)
    avlThemes = []

    for line in availableThemes:
        if not startmatch + 'all' in line:
            matchObj = re.search(startmatch + '([a-z]|-)*', line)
            if matchObj:
                avlThemes.append(matchObj.group().replace(startmatch, ''))

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


