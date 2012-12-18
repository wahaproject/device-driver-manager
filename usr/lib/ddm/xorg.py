#!/usr/bin/env python

#import sys
import os
import re
import functions
from glob import glob
from execcmd import ExecCmd

manufacturerDrivers = [
['ATI', ['fglrx', 'radeonhd', 'radeon', 'fbdev', 'vesa']],
['NVIDIA', ['nvidia', 'nouveau', 'fbdev', 'vesa']],
['VIA', ['chrome9', 'openchrome', 'unichrome']],
['INTEL', ['intel', 'fbdev', 'vesa']]
]

minimalXorg = 'Section "%s"\n  Identifier   "Device%s"\n  Driver       "%s"\nEndSection\n'
blDdmFileName = 'blacklist-ddm.conf'
regExpCommented = '#[\s]*blacklist[\s]*%s'
regExpUncommented = '[^#][\s]*blacklist[\s]*%s'


class XorgConf():

    def __init__(self, loggerObject, xorgConfPath='/etc/X11/xorg.conf'):
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xorg = xorgConfPath
        self.modprobeDir = '/etc/modprobe.d'

    # Return a list with hardware modules for a given manufacturer
    def getModules(self, manufacturer):
        modules = []
        man = manufacturer.upper()
        for manDrv in manufacturerDrivers:
            if manDrv[0] == man:
                modules = manDrv[1]
                break
        self.log.write('Modules for %s: %s' % (manufacturer, str(modules)), 'XorgConf.getManufacturerModules', 'debug')
        return modules

    # Return the module belonging to a given driver
    def getModuleForDriver(self, manufacturer, driver):
        foundModule = ''
        modules = self.getModules(manufacturer)
        for module in modules:
            if module in driver:
                foundModule = module
                break
        return foundModule

    # Return graphics module used by X.org
    def getUsedDriver(self):
        # find the most recent X.org log
        module = None
        logDir = '/var/log/'
        logPath = None
        maxTime = 0
        for f in glob(os.path.join(logDir, 'Xorg.*.log')):
            mtime = os.stat(f).st_mtime
            if mtime > maxTime:
                maxTime = mtime
                logPath = f

        # Open the log file
        lines = []
        with open(logPath) as f:
            lines = list(f.read().splitlines())

        # Search for "randr" in each line and check the previous line for the used module
        lineCnt = -1
        for line in lines:
            lineCnt += 1
            matchObj = re.search('\)\srandr\s', line, flags=re.IGNORECASE)
            if matchObj:
                prevLine = lines[lineCnt - 1].lower()
                module = self.matchModuleInString(prevLine)
                break

        self.log.write('Used graphics driver: %s' % module, 'XorgConf.getUsedModule', 'info')
        return module

    # Return the module found in a string (used by getUsedModule)
    def matchModuleInString(self, text):
        for manDrv in manufacturerDrivers:
            for mod in manDrv[1]:
                if mod in text:
                    return mod
        return None

    # Set the given module in xorg.conf
    # e.g.: Set the driver of the 1st Device section: a.setModule('Device', 0, 'fbdev')
    def setModule(self, section, position, module):
        try:
            position = str(position)

            # Backup self.xorg (incl. meta data)
            if os.path.exists(self.xorg):
                functions.backupFile(self.xorg)
            else:
                # No xorg.conf - create minimal xorg.conf
                self.log.write('No xorg.conf - create minimal xorg.conf', 'XorgConf.setModule', 'info')
                f = open(self.xorg, 'w')
                f.write(minimalXorg % ('Device', '0', 'vesa'))
                f.close()

            # Create a new section with the given parameters
            newSection = minimalXorg % (section, position, module)

            # Quick and dirty: open xorg.conf and replace section with new section
            f = open(self.xorg, 'r')
            xcont = f.read()
            f.close()

            regExp = 'section.*\"%s(.|\n)*?identifier.*%s\"(.|\n)*?endsection' % (section, position)
            replTuple = re.subn(regExp, newSection, xcont, flags=re.IGNORECASE)
            if replTuple[1] > 0:
                # Save to self.xorg
                f = open(self.xorg, 'w')
                f.write(replTuple[0])
                f.close()
                self.log.write('New xorg.conf written', 'XorgConf.setModule', 'info')
            else:
                # No match was found: append newSection
                f = open(self.xorg, 'a')
                f.write(newSection)
                f.close()
                self.log.write('New section appended to xorg.conf', 'XorgConf.setModule', 'info')

        except Exception, detail:
            self.log.write(detail, 'XorgConf.setModule', 'exception')

    # Set blacklisting for given module (if on=False: blacklist for given module is removed)
    def blacklistModule(self, module, on=True):
        blacklistFiles = self.getBlacklistFiles(module, True)
        if on:
            # Blacklist module
            for fle in blacklistFiles:
                blFile = None
                blCommFile = None
                if fle[1]:
                    blFile = fle[0]
                else:
                    blCommFile = fle[0]

                if blFile is None:
                    if blCommFile:
                        # Uncomment blacklist in found file
                        self.log.write('Uncomment blacklist %s in: %s' % (module, blCommFile), 'XorgConf.blacklistModule', 'debug')
                        functions.replaceStringInFile(regExpCommented % module, 'blacklist %s' % module, blCommFile)
                    else:
                        # Create new blacklist file
                        modPath = os.path.join(self.modprobeDir, blDdmFileName)
                        self.log.write('Blacklist %s in: %s' % (module, modPath), 'XorgConf.blacklistModule', 'debug')
                        modFile = open(modPath, 'w')
                        modFile.write('\nblacklist %s' % module)
                        modFile.close()
        else:
            # Remove module blacklist = comment blacklist line
            for fle in blacklistFiles:
                if fle[1]:
                    self.log.write('Remove blacklist %s from: %s' % (module, fle[0]), 'XorgConf.blacklistModule', 'debug')
                    functions.replaceStringInFile(regExpUncommented % module, '\n#blacklist %s' % module, fle[0])

    # Get all files where the given module is blacklisted
    # and whether its an actively blacklisted module (uncommented)
    def getBlacklistFiles(self, module, includeCommented=False):
        blFiles = []
        files = functions.getFilesAndFoldersRecursively(self.modprobeDir, True, False)

        for fle in files:
            fleList = os.path.splitext(fle)
            if fleList[len(fleList) - 1] == '.conf':
                # Open the file
                f = open(fle, 'r')
                fcont = f.read()
                f.close()
                # Get uncommented lines
                regExp = regExpUncommented % module
                matchObj = re.search(regExp, fcont, flags=re.IGNORECASE)
                if matchObj:
                    self.log.write('Blacklist %s found in: %s' % (module, fle), 'XorgConf.getBlacklistFile', 'debug')
                    blFiles.append([fle, True])

                # Get commented lines
                if includeCommented:
                    regExp = regExpCommented % module
                    matchObj = re.search(regExp, fcont, flags=re.IGNORECASE)
                    if matchObj:
                        self.log.write('Commented blacklist %s found in: %s' % (module, fle), 'XorgConf.getBlacklistFile', 'debug')
                        blFiles.append([fle, False])

        return blFiles
