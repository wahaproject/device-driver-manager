#!/usr/bin/env python

import functions
import re
from nvidia import Nvidia
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']
debianPackages = ['linux-headers-generic-pae','linux-image-generic-pae']
ubuntuPackages = ['linux-generic-pae','linux-headers-generic-pae','linux-image-generic-pae']

class PAE():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.distributionReleaseNumber = functions.getDistributionReleaseNumber()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.packages = ubuntuPackages
        if self.distribution == 'debian':
            self.packages = debianPackages
    
    # Check if the PAE kernel can be installed
    def getPae(self):
        hwList = []
        
        # Ubuntu is already PAE enabled from version 12.10 (Quantal): no need to check
        # https://help.ubuntu.com/community/EnablingPAE
        self.log.write('Distribution: ' + self.distribution + ' ' + str(self.distributionReleaseNumber), 'pae.getPae', 'debug')
        skipPae = False
        if self.distribution == 'ubuntu' and self.distributionReleaseNumber >= 12.10:
            skipPae = True
        
        if not skipPae:
            # Get the kernel release
            kernelRelease = self.ec.run('uname -r')
            if not 'amd64' in kernelRelease[0]:
                if not 'pae' in kernelRelease[0]:
                    self.log.write('Single-core kernel found: ' + kernelRelease[0], 'pae.getPae', 'debug')

                    # Check the machine hardware
                    machine = self.ec.run('uname -m')
                    if machine[0] == 'i686':
                        self.log.write('Multi-core system running single-core kernel found', 'pae.getPae', 'info')
                        # Check package status
                        status = packageStatus[0]
                        for package in self.packages:
                            if not functions.isPackageInstalled(package):
                                self.log.write('PAE not installed', 'pae.getPae', 'info')
                                status = packageStatus[1]
                                break
                        hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], status])
                    else:
                        self.log.write('PAE kernel cannot be installed: single-core system', 'pae.getPae', 'warning')
                    
                else:
                    self.log.write('Multi-core already installed: ' + kernelRelease[0], 'pae.getPae', 'info')
                    hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], packageStatus[0]])
                
        return hwList
    
    # Called from drivers.py: install PAE kernel
    def installPAE(self):
        try:
            cmdPae = 'apt-get -y --force-yes install'
            for package in self.packages:
                cmdPae += ' ' + package
            cmdPae += ' --reinstall'
            self.log.write('PAE kernel install command: ' + cmdPae, 'pae.installPAE', 'debug')
            self.ec.run(cmdPae)
            
            # Check for Nvidia
            nv = Nvidia(self.distribution, self.log)
            nvList = nv.getNvidia()
            self.log.write('Nvidia info: ' + str(nvList), 'pae.installPAE', 'debug')
            for nvInfo in nvList:
                if nvInfo[2] == packageStatus[0]:
                    self.log.write('Install Nvidia drivers', 'pae.installPAE', 'info')
                    nv.installNvidia()
            
            self.log.write('Done installing PAE', 'pae.installPAE', 'info')
                
        except Exception, detail:
            self.log.write(detail, 'pae.installPAE', 'error')
            
    # Called from drivers.py: remove the PAE kernel
    # TODO: I don't think this is going to work - test this
    def removePAE(self):
        try:
            kernelRelease = self.ec.run('uname -r')
            if not 'pae' in kernelRelease[0]:
                self.log.write('Not running pae, continue removal', 'pae.removePAE', 'debug')
                for package in self.packages:
                    cmdPurge = 'apt-get -y --force-yes purge ' + package
                    self.log.write('PAE package to remove: ' + package, 'pae.removePAE', 'info')
                    self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')
                self.log.write('Done removing PAE', 'pae.removePAE', 'info')
            else:
                self.log.write('Cannot remove PAE when running PAE', 'pae.removePAE', 'warning')
                
        except Exception, detail:
            self.log.write(detail, 'pae.removePAE', 'error')
    