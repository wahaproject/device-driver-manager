#!/usr/bin/env python

#import sys
import os
import re
import functions
import gettext
from glob import glob
from execcmd import ExecCmd

manufacturerDrivers = [
['ATI', ['fglrx', 'radeonhd', 'radeon', 'fbdev', 'vesa']],
['NVIDIA', ['nvidia', 'nouveau', 'fbdev', 'vesa']],
['VIA', ['chrome9', 'openchrome', 'unichrome']],
['INTEL', ['intel', 'fbdev', 'vesa']],
['ATI_INTEL', ['fglrx', 'intel', 'radeonhd', 'radeon', 'fbdev', 'vesa']],
['NVIDIA_INTEL', ['nvidia', 'intel', 'nouveau', 'fbdev', 'vesa']]
]

minimalXorg = 'Section "%s"\n  Identifier   "Device%s"\n  Driver       "%s"\nEndSection\n'
regExpCommented = '#[\s]*blacklist[\s]*%s'
regExpUncommented = '[^#][\s]*blacklist[\s]*%s'

# i18n
gettext.install("ddm", "/usr/share/locale")


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
        self.log.write("Modules for %(manufacturer)s: %(modules)s" % { "manufacturer": manufacturer, "modules": str(modules) }, 'XorgConf.getManufacturerModules', 'debug')
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
    # TODO: is lsmod an alternative?
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
        # Search for "depth" in each line and check the used module
        f = open(logPath, 'r')
        log = f.read()
        f.close()
        matchObj = re.search('([a-zA-Z]*)\(\d+\):\s+depth.*framebuffer', log, flags=re.IGNORECASE)
        if matchObj:
            module = matchObj.group(1).lower()

        self.log.write(_("Used graphics driver: %(module)s") % { "module": module }, 'XorgConf.getUsedModule', 'info')
        return module

    # Check if a module is supported by DDM
    def isModuleSupported(self, module):
        for manDrv in manufacturerDrivers:
            for mod in manDrv[1]:
                if mod == module:
                    return True
        return False

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
                self.log.write(_("No xorg.conf - create minimal xorg.conf"), 'XorgConf.setModule', 'info')
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
                self.log.write(_("New xorg.conf written"), 'XorgConf.setModule', 'info')
            else:
                # No match was found: append newSection
                f = open(self.xorg, 'a')
                f.write(newSection)
                f.close()
                self.log.write(_("New section appended to xorg.conf"), 'XorgConf.setModule', 'info')

        except Exception, detail:
            self.log.write(detail, 'XorgConf.setModule', 'exception')

    # Set blacklisting for given module (if on=False: blacklist for given module is removed)
    def blacklistModule(self, module, on=True):
        blacklistFiles = self.getBlacklistFiles(module, True)
        if on:
            # Blacklist module
            if not blacklistFiles:
                # Create new blacklist file
                modPath = os.path.join(self.modprobeDir, 'blacklist-%s.conf' % module)
                self.log.write("Blacklist %(module)s in: %(path)s" % { "module": module, "path": modPath }, 'XorgConf.blacklistModule', 'debug')
                modFile = open(modPath, 'w')
                modFile.write('blacklist %s' % module)
                modFile.close()
            else:
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
                            self.log.write("Uncomment blacklist %(module)s in: %(path)s" % { "module": module, "path": blCommFile }, 'XorgConf.blacklistModule', 'debug')
                            functions.replaceStringInFile(regExpCommented % module, 'blacklist %s' % module, blCommFile)
        else:
            # Remove module blacklist = comment blacklist line
            for fle in blacklistFiles:
                if fle[1]:
                    self.log.write("Remove blacklist %(module)s from: %(path)s" % { "module": module, "path": fle[0] }, 'XorgConf.blacklistModule', 'debug')
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
                    self.log.write("Blacklist %(module)s found in: %(path)s" % { "module": module, "path": fle }, 'XorgConf.getBlacklistFile', 'debug')
                    blFiles.append([fle, True])

                # Get commented lines
                if includeCommented:
                    regExp = regExpCommented % module
                    matchObj = re.search(regExp, fcont, flags=re.IGNORECASE)
                    if matchObj:
                        self.log.write("Commented blacklist %(module)s found in: %(path)s" % { "module": module, "path": fle }, 'XorgConf.getBlacklistFile', 'debug')
                        blFiles.append([fle, False])

        return blFiles
