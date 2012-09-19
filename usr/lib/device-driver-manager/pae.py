#!/usr/bin/env python

import functions
import shutil
import re
from nvidia import Nvidia
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
        kernelRelease = self.ec.run('uname -r')
        if '486' in kernelRelease[0]:
            self.log.write('Single-core kernel found: ' + kernelRelease[0], 'pae.getHardwareList', 'debug')

            # Check the machine hardware
            machine = self.ec.run('uname -m')
            if machine[0] == 'i686':
                self.log.write('Multi-core system running single-core kernel found', 'pae.getHardwareList', 'info')
                status = packageStatus[1]
                # Check if PAE is installed next to the i486 kernel
                paeInst = self.ec.run('apt search 686-pae | grep ^i')
                if paeInst:
                    self.log.write('PAE and i486 kernels installed', 'pae.getHardwareList', 'info')
                    status = packageStatus[0]
                hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], status])
            else:
                self.log.write('PAE kernel cannot be installed: single-core system', 'pae.getHardwareList', 'warning')
            
        elif '686' in kernelRelease[0]:
            self.log.write('Multi-core already installed: ' + kernelRelease[0], 'pae.getHardwareList', 'info')
            hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], packageStatus[0]])
                
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
            
            # Check for Nvidia
            nv = Nvidia(self.distribution, self.log)
            nvList = nv.getNvidia()
            self.log.write('Nvidia info: ' + str(nvList), 'pae.installPAE', 'debug')
            for nvInfo in nvList:
                if nvInfo[2] == packageStatus[0]:
                    self.log.write('Install Nvidia drivers', 'pae.installPAE', 'info')
                    nv.installNvidia()
            
            # Remove xorg.conf
            #xorg = '/etc/X11/xorg.conf'
            #if os.path.exists(xorg):
            #    shutil.move(xorg, xorg + '.ddm')
            #    self.log.write('Moved ' + xorg + ' to ' + xorg + '.ddm', 'pae.installPAE', 'info')
                
        except Exception, detail:
            self.log.write(detail, 'pae.installPAE', 'error')
            
    # Called from drivers.py: remove the PAE kernel
    # TODO: I don't think this is going to work - test this
    def removePAE(self):
        try:
            kernelRelease = self.ec.run('uname -r')
            if not '686' in kernelRelease[0]:
                self.log.write('Not running pae, continue removal', 'pae.removePAE', 'debug')
                paePackages = self.ec.run('apt search 686-pae | grep ^i', False)
                for line in paePackages:
                    paeMatch = re.search('linux[a-z0-9-\.]*', line)
                    if paeMatch:
                        pae = matchObj.group(0)
                        cmdPurge = 'apt-get -y --force-yes purge ' + pae
                        self.log.write('PAE package to remove: ' + pae, 'pae.removePAE', 'info')
                        self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')
            else:
                self.log.write('Cannot remove PAE when running PAE', 'pae.removePAE', 'warning')
                
        except Exception, detail:
            self.log.write(detail, 'pae.removePAE', 'error')
    