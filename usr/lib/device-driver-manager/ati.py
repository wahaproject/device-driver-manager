#!/usr/bin/env python

import os
import re
import functions
from config import Config
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae']
atiStartSerie = 5000


class ATI():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
    
    # Called from drivers.py: Check for ATI
    def getATI(self):
        # Check for ATI cards
        hwList = []
        cmdGraph = 'lspci | grep VGA'
        hwGraph = self.ec.run(cmdGraph)
        for line in hwGraph:
            hw = line[line.find(': ') + 2:]
            atiChk = re.search('\\b' + hwCodes[1] + '\\b', hw.lower())
            if atiChk:
                # Get the ATI chip set serie
                atiSerie = re.search('\b\d{4,5}\b', line)
                self.log.write('ATI chip serie found: ' + atiSerie, 'ati.getATI', 'info')
                if atiSerie:
                    intSerie = functions.strToInt(atiSerie.group(0))
                    # Only add series from atiStartSerie
                    if intSerie >= atiStartSerie:
                        drv = self.getDriver()
                        status = functions.getPackageStatus(drv)
                        self.log.write('ATI ' + drv + ' status: ' + status, 'ati.getATI', 'debug')
                        hwList.append([hw, hwCodes[1], status])
                    else:
                        self.log.write('ATI driver not installable', 'ati.getATI', 'warning')
                        hwList.append([hw, hwCodes[1], packageStatus[2]])
            else:
                self.log.write('No ATI card found', 'ati.getATI', 'debug')
        
        return hwList
    
    # Check distribution and get appropriate driver
    def getDriver():
        if self.distribution == 'debian':
            drv = 'fglrx-driver'
        else:
            drv = 'fglrx'
            
    # Get additional packages
    # The second value in the list is a numerical value (True=1, False=0) whether the package must be removed before installation
    def getAdditionalPackages(self, driver):
        drvList = []
        # Common packages
        drvList.append([driver, 1])
        drvList.append(['fglrx-control', 1])
        drvList.append(['build-essential', 0])
        drvList.append(['module-assistant', 0])
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
                    drvChkCmd = 'apt search ' + package[0] + ' | grep ^i | wc -l'
                    drvChk = self.ec.run(drvChkCmd, False)
                    if functions.strToInt(drvChk[0]) > 0:
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
            
            # Install the packages
            self.log.write('Install drivers: ' + installPackages, 'ati.installATIDriver', 'debug')
            nvDrvInstCmd = 'apt-get -y --force-yes install' + installPackages
            self.ec.run(nvDrvInstCmd)
            
        except Exception, detail:
            self.log.write(detail, 'ati.installATIDriver', 'exception')
    
    # Called from drivers.py: install the ATI drivers
    def installATI(self):
        try:
            # Check if alternative repo is necessary
            listFile = '/etc/apt/sources.list.d/altrad.list'
            conf = Config('ddm.conf')

            # Check if we need to use an alternative repository
            altRadeonRepo = ''
            if self.distribution == 'debian':
                altRadeonRepo = conf.getValue('Program', 'altRadeonRepoDebian')
            else:
                altRadeonRepo = conf.getValue('Program', 'altRadeonRepoUbuntu')
                
            if altRadeonRepo != '':
                self.log.write('Alternative repository for ATI drivers: ' + altRadeonRepo, 'ati.installATI', 'debug')
                modFile = open(listFile, 'w')
                modFile.write(altRadeonRepo)
                modFile.close()
                self.ec.run('apt-get update')
            
            # Install the driver and create xorg.conf
            drv = self.getDriver()
            if drv != '':
                self.log.write('ATI driver to install: ' + drv, 'ati.installATI', 'debug')
                packages = self.getAdditionalPackages(drv)
                self.installATIDriver(packages)
                # Configure ATI
                self.ec.run('aticonfig --initial -f')
                            
            # Remove the alternative repository
            if altRadeonRepo != '':
                self.log.write('Remove alternative Radeon repository: ' + altRadeonRepo, 'ati.installATI', 'debug')
                os.remove(listFile)
                self.ec.run('apt-get update')
                
        except Exception, detail:
            self.log.write(detail, 'ati.installATI', 'exception')
    
    # Called from drivers.py: remove the ATI drivers and revert to Nouveau
    def removeATI(self):
        try:
            self.log.write('Remove ATI drivers: fglrx', 'ati.removeATI', 'debug')
                
            self.ec.run('apt-get -y --force-yes purge fglrx*')
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-radeon xserver-xorg-video-nouveau xserver-xorg-video-ati libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa')
                
        except Exception, detail:
            self.log.write(detail, 'ati.removeATI', 'exception')