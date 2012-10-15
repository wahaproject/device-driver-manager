#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']
blacklistPath = '/etc/modprobe.d/blacklist-broadcom.conf'

# Chipsets and corresponding packages
# http://linuxwireless.org/en/users/Drivers/b43
bcChips = [
['576','firmware-brcm80211'],
['4301','firmware-b43legacy-installer'],
['4306','firmware-b43legacy-installer'],
['4307','firmware-b43-installer'],
['4311','firmware-b43-installer'],
['4312','firmware-b43-installer'], # This is not a BCM4312 but BCM4311
['4313','broadcom-sta-dkms'],
['4315','firmware-b43-lpphy-installer'], # This is BCM4312
['4318','firmware-b43-installer'],
['4319','firmware-b43-installer'],
['4320','firmware-b43-installer'],
['4321','firmware-b43-installer'],
['4324','firmware-b43-installer'],
['4325','firmware-b43legacy-installer'],
['4328','broadcom-sta-dkms'],
['4329','broadcom-sta-dkms'],
['432a','broadcom-sta-dkms'],
['432b','broadcom-sta-dkms'],
['432c','broadcom-sta-dkms'], # Better to use firmware-b43-installer?
['432d','broadcom-sta-dkms'],
['4331','firmware-b43-installer'],
['4353','firmware-brcm80211'],
['4357','firmware-brcm80211'],
['4358','broadcom-sta-dkms'],
['4359','broadcom-sta-dkms'],
['435a','broadcom-sta-dkms'],
['4727','firmware-brcm80211'], # May need blacklisting b43 on some kernels (up to 3.2?)
['a8d6','firmware-b43-installer'], # Untested, but the other drivers have no support at all
['a99d','broadcom-sta-dkms']
]

class Broadcom():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.status = ''
        self.currentChip = ''
        self.installableChip = ''
        self.installableDriver = ''
        self.hw = ''
    
    # Called from drivers.py: Check for Broadcom
    def getBroadcom(self):
        hwList = []
        self.setCurrentChipInfo()
        if self.hw != '':
            if self.currentChip != '':
                if self.installableChip != '':
                    self.log.write('Broadcom chip serie found: ' + self.installableChip, 'broadcom.getBroadcom', 'info')
                    hwList.append([self.hw, hwCodes[2], self.status])
                else:
                    # Broadcom was found, but no supported chip set: return uninstallable
                    self.log.write('Broadcom chip serie not supported: ' + self.currentChip, 'broadcom.getBroadcom', 'warning')
                    hwList.append([self.hw, hwCodes[2], packageStatus[2]])
            else:
                # Broadcom was found, but no chip set was found: return uninstallable
                self.log.write('Broadcom chip serie not detected: ' + self.hw, 'broadcom.getBroadcom', 'warning')
                hwList.append([self.hw, hwCodes[2], packageStatus[2]])
        
        return hwList
    
    # Check for Broadcom chip set and set variables
    def setCurrentChipInfo(self):
        hwList = []
        self.currentChip = ''
        self.installableDriver = ''
        self.status = ''
        
        # Get Broadcom info
        cmdBc = 'lspci | grep Broadcom' 
        hwBc = self.ec.run(cmdBc)
        if hwBc:
            self.hw = hwBc[0][hwBc[0].find(': ') + 2:]
            self.log.write('Broadcom found: ' + self.hw, 'broadcom.setCurrentChipInfo', 'info')
            # Get the chip set number
            cmdPciId = 'lspci -n -d 14e4:'
            pciId = self.ec.run(cmdPciId)
            if pciId:
                chipSet = re.search('14e4:([a-zA-Z0-9]*)', pciId[0])
                if chipSet:
                    self.currentChip = chipSet.group(1)
                    self.log.write('Broadcom chip set found: ' + self.currentChip, 'broadcom.setCurrentChipInfo', 'debug')
                    for chipList in bcChips:
                        if self.currentChip == chipList[0]:
                            # Supported chipset found: set variables
                            self.log.write('Broadcom chip set driver: ' + chipList[1], 'broadcom.setCurrentChipInfo', 'debug')
                            self.installableChip = chipList[0]
                            self.installableDriver = chipList[1]
                            self.status = functions.getPackageStatus(chipList[1])
                            break
                    # Check if a supported chip set is found
                    if self.installableChip == '':
                        self.log.write('Broadcom chip set not supported: ' + self.hw, 'broadcom.setCurrentChipInfo', 'error')
                else:
                    self.log.write('Broadcom chip set not found: ' + pciId[0], 'broadcom.setCurrentChipInfo', 'warning')
            else:
                self.log.write('Broadcom pci ID not found: ' + self.hw, 'broadcom.setCurrentChipInfo', 'warning')
    

    # Install the broadcom drivers
    def installBroadcom(self):
        try:
            self.setCurrentChipInfo()
            if self.installableDriver != '':
                # Get the correct linux header package
                linHeader = self.ec.run("echo linux-headers-$(uname -r|sed 's,[^-]*-[^-]*-,,')", False)
                self.log.write('Linux header name to install: ' + linHeader[0], 'broadcom.installBroadcom', 'info')
                
                # Only install linux header if it is not installed
                if not functions.isPackageInstalled(linHeader[0]):
                    self.log.write('Download package: ' + linHeader[0], 'broadcom.installBroadcom', 'info')
                    self.ec.run('apt-get download ' + linHeader[0])
                    
                # Download the driver and its dependencies
                cmdBc = 'apt-get download ' + self.installableDriver 
                self.log.write('Download package: ' + self.installableDriver, 'broadcom.installBroadcom', 'info')
                self.ec.run(cmdBc)
                depList = functions.getPackageDependencies(self.installableDriver)
                for dep in depList:
                    if not functions.isPackageInstalled(dep):
                        cmdDep = 'apt-get download ' + dep
                        self.log.write('Download package dependency: ' + dep, 'broadcom.installBroadcom', 'debug')
                        self.ec.run(cmdDep)
                
                # Remove any module that might be in the way
                self.log.write('modprobe b44, b43, b43legacy, ssb, brcmsmac', 'broadcom.installBroadcom', 'debug')
                os.system('modprobe -rf b44')
                os.system('modprobe -rf b43')
                os.system('modprobe -rf b43legacy')
                os.system('modprobe -rf ssb')
                os.system('modprobe -rf brcmsmac')
                
                # Install the dowloaded packages
                self.log.write('Install downloaded packages', 'broadcom.installBroadcom', 'info')
                self.ec.run('dpkg -i *.deb')
                # Delete the downloaded packages
                self.log.write('Remove downloaded debs', 'broadcom.installBroadcom', 'debug')
                os.system('rm -f *.deb')
                
                # Finish up
                if self.installableDriver == 'broadcom-sta-dkms':
                    # Blacklist b43, brcmsmac
                    self.log.write('blacklist b43 brcmsmac bcma ssb', 'broadcom.installBroadcom', 'debug')
                    modFile = open(blacklistPath, 'w')
                    modFile.write('blacklist b43 brcmsmac bcma ssb')
                    modFile.close()
                    # Start wl
                    self.log.write('modprobe wl', 'broadcom.installBroadcom', 'debug')
                    os.system('modprobe wl')
                elif 'b43' in self.installableDriver:
                    # Start b43
                    self.log.write('modprobe b43', 'broadcom.installBroadcom', 'debug')
                    os.system('modprobe b43')
                else:
                    # Start brcmsmac
                    self.log.write('modprobe brcmsmac', 'broadcom.installBroadcom', 'debug')
                    os.system('modprobe brcmsmac')
                    
                self.log.write('Done installing Broadcome drivers', 'broadcom.installBroadcom', 'info')
            else:
                self.log.write('No Broadcom chip set found', 'broadcom.installBroadcom', 'error')
                
        except Exception, detail:
            self.log.write(detail, 'broadcom.installBroadcom', 'exception')
    
    # Remove the broadcom drivers
    def removeBroadcom(self):
        try:
            self.setCurrentChipInfo()
            if self.installableDriver != '':
                self.log.write('Purge driver: ' + self.installableDriver, 'broadcom.removeBroadcom', 'info')
                cmdPurge = 'apt-get -y --force-yes purge ' + self.installableDriver
                self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')
                
                # Remove blacklist Nouveau
                if os.path.exists(blacklistPath):
                    self.log.write('Remove : ' + blacklistPath, 'broadcom.removeBroadcom', 'debug')
                    os.remove(blacklistPath)
                    
                self.log.write('Done removing Broadcome drivers', 'broadcom.removeBroadcom', 'info')
                
        except Exception, detail:
            self.log.write(detail, 'broadcom.removeBroadcom', 'exception')
