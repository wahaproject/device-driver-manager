#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'intel', 'via', 'broadcom', 'pae']
atiStartSerie = 5000


class ATI():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        self.hw = functions.getGraphicsCards('1002')
        self.drivers = []

        # Test (01:00.0 VGA compatible controller [0300]: Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series] [1002:68e0])
        #self.hw = ['Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series]']

        if self.hw:
            if self.distribution == 'debian':
                # Add Debian driver
                self.drivers.append('fglrx-driver')
            else:
                # Ubuntu
                self.drivers.append('fglrx')
            # Additional drivers
            self.drivers.append('xserver-xorg-video-radeon')
            self.drivers.append('xserver-xorg-video-fbdev')
            self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for ATI
    def getATI(self):
        # Check for ATI cards
        hwList = []
        for card in self.hw:
            self.log.write('ATI card found: %s' % card, 'ati.getATI', 'info')
            # Get the ATI chip set serie
            atiSerie = re.search('\s\d{4,}', card)
            if atiSerie:
                self.log.write('ATI chip serie found: %s' % atiSerie.group(0), 'ati.getATI', 'info')
                intSerie = functions.strToNumber(atiSerie.group(0))
                # Only add series from atiStartSerie
                if intSerie >= atiStartSerie:
                    for drv in self.drivers:
                        status = functions.getPackageStatus(drv)
                        version = functions.getPackageVersion(drv, True)
                        description = self.getDriverDescription(drv)
                        if status != packageStatus[2]:
                            self.log.write('ATI driver found: %s (%s)' % (drv, status), 'ati.getATI', 'info')
                            hwList.append([card, hwCodes[1], status, drv, version, description])
                        else:
                            self.log.write('Driver not installable: %s' % drv, 'ati.getATI', 'warning')
                else:
                    self.log.write('ATI chip serie not supported: %s' % str(intSerie), 'ati.getATI', 'warning')
            else:
                self.log.write('No ATI chip serie found: %s' % card, 'ati.getATI', 'warning')

        return hwList

    # Called from drivers.py: install the ATI drivers
    def installATI(self, driver):
        try:
            isConfigured = False
            module = self.xc.getModuleForDriver(hwCodes[1], driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write('Install driver: %s' % driver, 'ati.installATI', 'info')
                packages = self.getAdditionalPackages(driver)
                self.installATIDriver(packages)
                # Configure ATI
                if module == 'fglrx':
                    self.log.write('Configure ATI...', 'ati.installATI', 'debug')
                    self.ec.run('aticonfig --initial -f')
                    isConfigured = True

            if not isConfigured:
                # Configure xorg.conf
                self.log.write('Found module for driver %s: %s' % (driver, module), 'ati.installATI', 'debug')
                if module != '':
                    self.log.write('Switch to module: %s' % module, 'ati.installATI', 'info')
                    if module == 'fglrx':
                        self.ec.run('aticonfig --initial -f')
                    else:
                        self.xc.setModule('Device', 0, module)

            self.log.write('Driver installed: %s' % driver, 'ati.installATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.installATI', 'exception')

    # Called from drivers.py: remove the ATI drivers and revert to radeon
    def removeATI(self, driver):
        try:
            # Preseed answers for some packages
            self.preseedATIPackages('purge')

            self.log.write('Removing ATI drivers', 'ati.removeATI', 'info')
            packages = self.getAdditionalPackages(driver)
            for package in packages:
                self.log.write('Remove package: %s' % package[0], 'ati.removeATI', 'debug')
                cmdPurge = 'apt-get -y --force-yes purge %s' % package[0]
                self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have all open drivers available
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-radeon xserver-xorg-video-ati xserver-xorg-video-fbedev xserver-xorg-video-vesa libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write('Driver removed: %s' % driver, 'ati.removeATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.removeATI', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'fglrx' in driver:
            description = 'ATI display driver'
        elif 'radeon' in driver:
            description = 'Radeon display driver'
        elif 'fbdev' in driver:
            description = 'Framebuffer display driver'
        elif 'vesa' in driver:
            description = 'Vesa display driver'
        else:
            description = functions.getPackageDescription(driver)
        return description

    # Get additional packages
    # The second value in the list is a numerical value:
    # 0 = Need to install, but removal before reinstallation is not needed
    # 1 = Need to install and removal is needed before reinstallation
    # 2 = Optional install
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getLinuxHeadersAndImage()
        drvList.append([linHeader[0], 0])
        # Common packages
        if self.distribution == 'debian':
            if 'fglrx' in driver:
                drvList.append(['build-essential', 0])
                drvList.append(['module-assistant', 0])
                drvList.append([driver, 1])
                drvList.append(['fglrx-modules-dkms', 1])
                drvList.append(['libgl1-fglrx-glx', 1])
                drvList.append(['glx-alternative-fglrx', 0])
                drvList.append(['fglrx-control', 1])
                drvList.append(['fglrx-glx-ia32', 2])
            else:
                # Radeon, fbdev, vesa
                drvList.append([driver, 1])
        else:
            drvList.append([driver, 1])
            if 'fglrx' in driver:
                drvList.append(['fglrx-amdcccle', 1])
        return drvList

    # Install the given packages
    def installATIDriver(self, packageList):
        try:
            # Remove certain packages before installing the drivers
            for package in packageList:
                if package[1] == 1:
                    if functions.isPackageInstalled(package[0]):
                        self.log.write('Remove package: %s' % package[0], 'ati.installATIDriver', 'debug')
                        self.ec.run('apt-get -y --force-yes remove %s' % package[0])

            # Preseed answers for some packages
            self.preseedATIPackages('install')

            # Install the packages
            installString = ''
            notInRepo = ''
            for package in packageList:
                chkStatus = functions.getPackageStatus(package[0])
                if chkStatus != packageStatus[2]:
                    installString += ' ' + package[0]
                elif package[1] != 2:
                    notInRepo += ', ' + package[0]

            if notInRepo == '':
                self.ec.run('apt-get -y --force-yes install' + installString)
            else:
                self.log.write('Install aborted: not in repository: %s' % notInRepo[2:], 'ati.installATIDriver', 'error')

        except Exception, detail:
            self.log.write(detail, 'ati.installATIDriver', 'exception')

    def preseedATIPackages(self, action):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep fglrx > debconf-fglrx.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            debConfList.append('libfglrx fglrx-driver/check-for-unsupported-gpu boolean false')
            debConfList.append('fglrx-driver fglrx-driver/check-xorg-conf-on-removal boolean false')
            debConfList.append('libfglrx fglrx-driver/install-even-if-unsupported-gpu-exists boolean false')
            debConfList.append('fglrx-driver fglrx-driver/removed-but-enabled-in-xorg-conf note ')
            debConfList.append('fglrx-driver fglrx-driver/needs-xorg-conf-to-enable note ')

            # Add each line to the debconf database
            for line in debConfList:
                os.system('echo "%s" | debconf-set-selections' % line)

            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes %s libfglrx fglrx-driver' % action)
