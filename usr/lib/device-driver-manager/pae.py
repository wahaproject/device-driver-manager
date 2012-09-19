#!/usr/bin/env python

import functions
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae']

class PAE():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
    
    # Check if the PAE kernel for i486 can be installed
    def getPae(self):
        hwList = []
        # Get the kernel release
        hwName = self.ec.run('uname -m', False)
        if hwName[0] == 'i486':
            self.log.write('Machine hardware name: ' + hwName[0], 'pae.getHardwareList', 'debug')
            
            # Check if there's more than 1 cpu
            # Cannot use lspci: acpi limits nr of cpus to 1 with 486 kernel
            # demsg | grep CPU returns: [ 0.000000] ACPI: NR_CPUS/possible_cpus limit of 1 reached. Processor 1/0x1 ignored.
            hwCpu = self.ec.run('dmesg | grep CPU | grep ignored', False)
            if hwCpu[0] != '':
                self.log.write('Multi-core system with single-core kernel found', 'pae.getHardwareList', 'info')
                hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], packageStatus[1]])
            else:
                self.log.write('PAE kernel cannot be installed: single-core system', 'pae.getHardwareList', 'debug')
            
        elif hwName[0] == 'i686':
            self.log.write('Multi-core already installed', 'pae.getHardwareList', 'info')
                
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
    