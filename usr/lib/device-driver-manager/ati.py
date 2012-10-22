#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']
atiStartSerie = 5000


class ATI():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.hw = functions.getGraphicsCard()

        # Test
        #self.hw = '00:01.0 VGA compatible controller: Advanced Micro Devices [AMD] nee ATI Wrestler [Radeon HD 6310]'
    
    # Called from drivers.py: Check for ATI
    def getATI(self):
        # Check for ATI cards
        hwList = []
        # Is it ATI?
        nvChk = re.search('\\b' + hwCodes[1] + '\\b', self.hw.lower())
        if nvChk:
            self.log.write('ATI card found: ' + self.hw, 'ati.getATI', 'info')
            # Get the ATI chip set serie
            atiSerie = re.search('\s\d{4,}', self.hw)
            if atiSerie:
                self.log.write('ATI chip serie found: ' + atiSerie.group(0), 'ati.getATI', 'info')
                intSerie = functions.strToNumber(atiSerie.group(0))
                # Only add series from atiStartSerie
                if intSerie >= atiStartSerie:
                    drv = self.getDriver()
                    status = functions.getPackageStatus(drv)
                    self.log.write('ATI ' + drv + ' status: ' + status, 'ati.getATI', 'debug')
                    hwList.append([self.hw, hwCodes[1], status])
                else:
                    self.log.write('ATI chip serie not supported: ' + str(intSerie), 'ati.getATI', 'warning')
                    hwList.append([self.hw, hwCodes[1], packageStatus[2]])
            else:
                self.log.write('No ATI chip serie found: ' + self.hw, 'ati.getATI', 'warning')
                hwList.append([self.hw, hwCodes[1], packageStatus[2]])

        return hwList
    
    # Check distribution and get appropriate driver
    def getDriver(self):
        drv = ''
        if self.distribution == 'debian':
            drv = 'fglrx-driver'
        else:
            drv = 'fglrx'
        return drv
            
    # Get additional packages
    # The second value in the list is a numerical value (True=1, False=0) whether the package must be removed before installation
    def getAdditionalPackages(self, driver):
        drvList = []
        # Common packages
        drvList.append([driver, 1])
        if self.distribution == 'debian':
            drvList.append(['fglrx-control', 1])
            drvList.append(['build-essential', 0])
            drvList.append(['module-assistant', 0])
            drvList.append(['fglrx-glx-ia32', 0])
        else:
            drvList.append(['fglrx-amdcccle', 1])
        return drvList
    
    # Install the given packages
    def installATIDriver(self, packageList):
        try:
            removePackages = ''
            installPackages = ''
            # Check if drivers are available in the repositories
            for package in packageList:
                # Build install packages string
                installPackages += ' ' + package[0]
                if package[1] == 1:
                    # Check if package is installed
                    # If it is, it's nominated for removal
                    self.log.write('Is package installed: ' + package[0], 'ati.installATIDriver', 'debug')
                    if functions.isPackageInstalled(package[0]):
                        # Build remove packages string
                        removePackages += ' ' + package[0]
            
            # Remove these packages before installation
            if removePackages != '':
                self.log.write('Remove drivers before reinstallation: ' + removePackages, 'ati.installATIDriver', 'debug')
                nvDrvRemCmd = 'apt-get -y --force-yes remove' + removePackages
                self.ec.run(nvDrvRemCmd)
                
            # Purge Nouveau (TODO: is this really necessary?)
            self.log.write('Purge Nouveau drivers: xserver-xorg-video-nouvea', 'ati.installATIDriver', 'debug')
            self.ec.run('apt-get -y --force-yes remove xserver-xorg-video-nouveau')
            
            # Preseed answers for some packages
            self.preseedATIPackages('install')
            
            # Install the packages
            self.log.write('Install drivers: ' + installPackages, 'ati.installATIDriver', 'debug')
            nvDrvInstCmd = 'apt-get -y --force-yes install' + installPackages
            self.ec.run(nvDrvInstCmd)
            
        except Exception, detail:
            self.log.write(detail, 'ati.installATIDriver', 'exception')
    
    # Called from drivers.py: install the ATI drivers
    def installATI(self):
        try:          
            # Install the driver and create xorg.conf
            drv = self.getDriver()
            if drv != '':
                self.log.write('ATI driver to install: ' + drv, 'ati.installATI', 'info')
                packages = self.getAdditionalPackages(drv)
                self.installATIDriver(packages)
                # Configure ATI
                xorg = '/etc/X11/xorg.conf'
                if os.path.exists(xorg):
                    self.log.write('Copy ' + xorg + ' to ' + xorg + '.ddm.bak', 'ati.installATI', 'info')
                    self.ec.run('cp ' + xorg + ' ' + xorg + '.ddm.bak')
                self.log.write('Configure ATI', 'ati.installATI', 'debug')
                self.ec.run('aticonfig --initial -f')
                
                self.log.write('Done installing ATI drivers', 'ati.installATI', 'info')
                
        except Exception, detail:
            self.log.write(detail, 'ati.installATI', 'exception')
    
    # Called from drivers.py: remove the ATI drivers and revert to Nouveau
    def removeATI(self):
        try:
            self.log.write('Remove ATI drivers: fglrx', 'ati.removeATI', 'debug')
            
            # Preseed answers for some packages
            self.preseedATIPackages('purge')
                
            self.ec.run('apt-get -y --force-yes purge fglrx*')
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-radeon xserver-xorg-video-nouveau xserver-xorg-video-ati libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa')
            
            # Rename xorg.conf
            xorg = '/etc/X11/xorg.conf'
            if os.path.exists(xorg):
                self.log.write('Rename : ' + xorg + ' -> ' + xorg + '.ddm.bak', 'nvidia.removeNvidia', 'debug')
                os.rename(xorg, xorg + '.ddm.bak')
                
            self.log.write('Done removing ATI drivers', 'ati.removeATI', 'info')
                
        except Exception, detail:
            self.log.write(detail, 'ati.removeATI', 'exception')
            
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
                os.system('echo "' + line + '" | debconf-set-selections')
            
            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes ' + action + ' libfglrx fglrx-driver')
