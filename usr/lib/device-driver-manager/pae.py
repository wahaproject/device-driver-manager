#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae']

class PAE():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
    
    # Check if the PAE kernel for i386 can be installed
    def getPae(self):
        hwList = []
        # Get the number of CPUs
        cmdCpus = 'cat /proc/cpuinfo | grep processor | wc -l'
        hwCpus = self.ec.run(cmdCpus, False)
        
        # Get the kernel release
        cmdKernel = 'uname -r'
        kernelRelease = self.ec.run(cmdKernel, False)
        for nr in hwCpus:
            if functions.strToInt(nr) > 1:
                self.log.write('Nr. of cpus: ' + nr, 'pae.getHardwareList', 'debug')
                for kr in kernelRelease:
                    self.log.write('Kernel release: ' + kr, 'pae.getHardwareList', 'debug')
                    if '486' in kr:
                        self.log.write('Multi-core system with single-core kernel found', 'pae.getHardwareList', 'info')
                        status = functions.getPackageStatus('linux-headers-686-pae')
                        hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], status])
                        break
                    
        return hwList
    
    # Called from drivers.py: install PAE kernel
    def installPAE(self):
        try:
            cmdPae = 'apt-get -y --force-yes install linux-headers-686-pae linux-image-686-pae'
            # Check if already installed
            status = functions.getPackageStatus('linux-headers-686-pae')
            if status == packageStatus[0]:
                cmdPae += ' --reinstall'
            self.log.write('PAE kernel install command: ' + cmdPae, 'pae.installPAE', 'debug')
            self.ec.run(cmdPae)
                
        except Exception, detail:
            self.log.write(detail, 'pae.installPAE', 'error')
    
    # Called from drivers.py: remove the PAE kernel
    # TODO: I don't think this is going to work - test this
    def removePAE(self):
        try:
            cmdPurge = 'apt-get -y --force-yes purge linux-headers-686-pae linux-image-686-pae'
            cmdInstall = 'apt-get -y --force-yes install linux-headers-486 linux-image-486'
            self.log.write('PAE kernel remove command: ' + cmdPurge, 'pae.removePAE', 'debug')
            self.log.write('486 kernel install command: ' + cmdInstall, 'pae.removePAE', 'debug')
            self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run(cmdInstall)
                
        except Exception, detail:
            self.log.write(detail, 'pae.removePAE', 'error')