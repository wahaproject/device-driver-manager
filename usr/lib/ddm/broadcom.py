#!/usr/bin/env python

import os
import re
import functions
import gettext
from execcmd import ExecCmd
from glob import glob

# i18n
gettext.install("ddm", "/usr/share/ddm/locale")

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'intel', 'via', 'broadcom', 'pae']
blacklistPath = '/etc/modprobe.d/blacklist-broadcom.conf'
# Driver package names
wlDebian = 'broadcom-sta-dkms'
wlUbuntu = 'bcmwl-kernel-source'
brcmDebian = 'firmware-brcm80211'
brcmUbuntu = 'brcmsmac'
b43legacy = 'firmware-b43legacy-installer'
b43 = 'firmware-b43-installer'
lpphy = 'firmware-b43-lpphy-installer'

# Chipsets and corresponding packages
# http://linuxwireless.org/en/users/Drivers/b43
# http://www.broadcom.com/docs/linux_sta/README.txt
# https://help.ubuntu.com/community/WifiDocs/Driver/bcm43xx#b43%20-%20Internet%20access
# [ChipID, DebianPackages, UbuntuPackages]
bcChips = [
['576', [brcmDebian, wlDebian], [brcmUbuntu, wlUbuntu]],
['4301', [b43legacy], [b43legacy]],
['4306', [b43legacy], [b43legacy]],
['4307', [b43], [b43]],
['4311', [b43, wlDebian], [b43, wlUbuntu]],
['4312', [b43, wlDebian], [b43, wlUbuntu]],    # This is not a BCM4312 but BCM4311
['4313', [wlDebian], [wlUbuntu]],
['4315', [b43, wlDebian], [b43, wlUbuntu]],    # This is BCM4312
['4318', [b43], [b43]],
['4319', [b43], [b43]],
['4320', [b43, b43legacy], [b43, b43legacy]],
['4321', [b43], [b43]],
['4322', [], []],
['4324', [b43, b43legacy], [b43, b43legacy]],
['4325', [b43legacy], [b43legacy]],
['4328', [wlDebian], [wlUbuntu]],
['4329', [wlDebian], [wlUbuntu]],
['432a', [wlDebian], [wlUbuntu]],
['432b', [wlDebian], [wlUbuntu]],
['432c', [b43, wlDebian], [b43, wlUbuntu]],    # Better to use firmware-b43-installer?
['432d', [wlDebian], [wlUbuntu]],
['4331', [b43], [b43]],
['4350', [b43], [b43]],
['4353', [b43, brcmDebian, wlDebian], [b43, brcmUbuntu, wlUbuntu]],
['4357', [b43, brcmDebian, wlDebian], [b43, brcmUbuntu, wlUbuntu]],
['4358', [wlDebian], [wlUbuntu]],
['4359', [wlDebian], [wlUbuntu]],
['435a', [wlDebian], [wlUbuntu]],
['4360', [], []],
['4365', [], []],
['43b1', [], []],
['4727', [brcmDebian, wlDebian], [brcmUbuntu, wlUbuntu]],    # May need blacklisting b43 on some kernels (up to 3.2?)
['a8d6', [b43], [b43]],    # Untested, but the other drivers have no support at all
['a8d8', [b43, brcmDebian], [b43, brcmUbuntu]],
['a99d', [wlDebian], [wlUbuntu]]
]


class Broadcom():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.status = ''
        self.currentChip = ''
        self.installableChip = ''
        self.installableDrivers = []
        self.hw = ''

    # Called from drivers.py: Check for Broadcom
    def getBroadcom(self):
        hwList = []
        self.setCurrentChipInfo()
        if self.hw != '':
            if self.currentChip != '':
                if self.installableChip != '':
                    self.log.write(_("Broadcom chip serie found: %(chip)s") % { "chip": self.installableChip }, 'broadcom.getBroadcom', 'info')
                    if self.installableDrivers:
                        for drv in self.installableDrivers:
                            # Check if you already have wireless
                            if functions.hasWireless():
                                status = packageStatus[0]
                            else:
                                status = functions.getPackageStatus(drv)
                            # Get the driver version
                            drvVersion = functions.getPackageVersion(drv, True)

                            hwList.append([self.hw, hwCodes[4], status, drv, drvVersion, 'Broadcom wireless'])
                    else:
                        # Broadcom chipset was found, but no drivers are available: return uninstallable
                        hwList.append([self.hw, hwCodes[4], packageStatus[2], '', '', 'Chipset not supported'])
                else:
                    # Broadcom was found, but no supported chip set: return uninstallable
                    hwList.append([self.hw, hwCodes[4], packageStatus[2], '', '', 'Chipset not supported'])
            else:
                # Broadcom was found, but no chip set was found: return uninstallable
                hwList.append([self.hw, hwCodes[4], packageStatus[2], '', '', 'Chipset not found'])

        return hwList

    # Return used wireless driver
    def getUsedDriver(self):
        driver = None
        logDir = '/var/log/'
        for logPath in glob(os.path.join(logDir, 'syslog*')):
            if driver is None and not 'gz' in logPath:
                # Open the log file
                lines = []
                with open(logPath) as f:
                    lines = list(f.read().splitlines())

                for line in reversed(lines):
                    # First check for Network Manager entry
                    # Search for wlan0 in each line and get the listed driver
                    matchObj = re.search('\(wlan\d\):.*driver:\s\'([a-z]*)', line, flags=re.IGNORECASE)
                    if matchObj:
                        driver = matchObj.group(1)
                        break
                    else:
                        # Wicd
                        # Search for ieee in each line and get the listed driver
                        matchObj = re.search('ieee.*implement', line, flags=re.IGNORECASE)
                        if matchObj:
                            driver = matchObj.group(0)
                            break

        if driver:
            if 'brcm' in driver:
                if self.distribution == 'debian':
                    driver = brcmDebian
                else:
                    driver = brcmUbuntu
            elif 'b43legacy' in driver:
                driver = b43legacy
            elif 'b43' in driver:
                driver = b43
            elif 'wl' in driver:
                if self.distribution == 'debian':
                    driver = wlDebian
                else:
                    driver = wlUbuntu
            elif 'lpphy' in driver:
                # TODO: check this out!
                driver = lpphy

        self.log.write(_("Used wireless driver: %(drv)s") % { "drv": driver }, 'broadcom.getUsedDriver', 'info')
        return driver

    # Check for Broadcom chip set and set variables
    def setCurrentChipInfo(self):
        self.currentChip = ''
        self.installableDriver = ''
        self.status = ''

        # Get Broadcom info
        cmdBc = 'lspci | grep -i Broadcom'
        hwBc = self.ec.run(cmdBc)

        # Test: not show
        #hwBc.append('03:00.0 Ethernet controller: Broadcom Corporation NetLink BCM57788 Gigabit Ethernet PCIe (rev 01)')

        if hwBc:
            for bc in hwBc:
                # Check if this a wired chipset
                if not 'ethernet controller' in bc.lower():
                    self.hw = bc[bc.find(': ') + 2:]
                    self.log.write(_("Broadcom found: %(broadcom)s") % { "broadcom": self.hw }, 'broadcom.setCurrentChipInfo', 'info')
                    # Get the chip set number
                    cmdPciId = 'lspci -n -d 14e4:'
                    pciId = self.ec.run(cmdPciId)
                    for pid in pciId:
                        chipSet = re.search('14e4:([a-zA-Z0-9]*)', pid)
                        if chipSet:
                            self.currentChip = chipSet.group(1)
                            self.log.write(_("Broadcom chip set found: %(chip)s") % { "chip": self.currentChip }, 'broadcom.setCurrentChipInfo', 'debug')
                            for chipList in bcChips:
                                if self.currentChip == chipList[0]:
                                    # Supported chipset found: set variables
                                    self.installableChip = chipList[0]
                                    if self.distribution == 'debian':
                                        for drv in chipList[1]:
                                            self.installableDrivers.append(drv)
                                    else:
                                        # Assume Ubuntu
                                        for drv in chipList[2]:
                                            self.installableDrivers.append(drv)
                                    break
                            # Check if a supported chip set is found
                            if self.installableChip == '':
                                self.log.write(_("Broadcom chipset not supported or ethernet controller: %(broadcom)s") % { "broadcom": self.hw }, 'broadcom.setCurrentChipInfo', 'warning')
                        else:
                            self.log.write(_("Broadcom chipset not found: %(chip)s") % { "chip": pciId[0] }, 'broadcom.setCurrentChipInfo', 'warning')
                    else:
                        self.log.write(_("Broadcom pci ID not found: %(id)s") % { "id": self.hw }, 'broadcom.setCurrentChipInfo', 'warning')

    # Install the broadcom drivers
    def installBroadcom(self, driver):
        try:
            if driver != '':
                debDownloaded = False
                # Get the correct linux header package
                linHeader = functions.getLinuxHeadersAndImage()
                self.log.write(_("Linux header name to install: %(header)s") % { "header": linHeader[0] }, 'broadcom.installBroadcom', 'info')

                # Only install linux header if it is not installed
                if not functions.isPackageInstalled(linHeader[0]):
                    self.log.write(_("Download package: %(package)s") % { "package": linHeader[0] }, 'broadcom.installBroadcom', 'info')
                    self.ec.run('apt-get download %s' % linHeader[0])
                    debDownloaded = True

                # Download the driver and its dependencies
                reconfPackages = []
                if driver != brcmUbuntu:
                    if not functions.isPackageInstalled(driver):
                        self.log.write(_("Download package: %(drv)s") % { "drv": driver }, 'broadcom.installBroadcom', 'info')
                        self.ec.run('apt-get download %s' % driver)
                        debDownloaded = True
                    else:
                        reconfPackages.append(driver)
                    depList = functions.getPackageDependencies(driver)
                    for dep in depList:
                        if not functions.isPackageInstalled(dep):
                            self.log.write(_("Download package dependency: %(dep)s") % { "dep": dep }, 'broadcom.installBroadcom', 'debug')
                            self.ec.run('apt-get download %s' % dep)
                            debDownloaded = True
                        else:
                            reconfPackages.append(dep)

                # Remove any module that might be in the way
                self.log.write(_("Modprobe b44, b43, b43legacy, ssb, brcmsmac"), 'broadcom.installBroadcom', 'debug')
                os.system('modprobe -rf b44')
                os.system('modprobe -rf b43')
                os.system('modprobe -rf b43legacy')
                os.system('modprobe -rf ssb')
                os.system('modprobe -rf brcmsmac')

                # When driver to install is not wl, we need to purge wl
                if self.distribution == 'debian':
                    if driver != wlDebian:
                        if functions.isPackageInstalled(wlDebian):
                            self.ec.run('apt-get -y --force-yes purge %s' % wlDebian)
                else:
                    if driver != wlUbuntu:
                        if functions.isPackageInstalled(wlUbuntu):
                            self.ec.run('apt-get -y --force-yes purge %s' % wlUbuntu)

                # Install the dowloaded packages
                if debDownloaded:
                    self.log.write(_("Install downloaded packages"), 'broadcom.installBroadcom', 'info')
                    self.ec.run('dpkg -i *.deb')
                    # Delete the downloaded packages
                    self.log.write(_("Remove downloaded debs"), 'broadcom.installBroadcom', 'debug')
                    os.system('rm -f *.deb')

                # Reconfigure packages when needed
                for reconfPackage in reconfPackages:
                    self.log.write(_("Reconfigure package: %(package)s") % { "package": reconfPackage }, 'broadcom.installBroadcom', 'info')
                    self.ec.run('dpkg-reconfigure -u %s' % reconfPackage)

                # Finish up
                if driver == wlDebian or driver == wlUbuntu:
                    # Blacklist b43, brcmsmac
                    self.log.write(_("Blacklist b43, brcmsmac, bcma, ssb"), 'broadcom.installBroadcom', 'debug')
                    modFile = open(blacklistPath, 'w')
                    modFile.write('blacklist b43 brcmsmac bcma ssb')
                    modFile.close()
                    # Start wl
                    self.log.write(_("Modprobe wl"), 'broadcom.installBroadcom', 'debug')
                    os.system('modprobe wl')
                else:
                    if os.path.isfile(blacklistPath):
                        os.remove(blacklistPath)
                    if 'b43legacy' in driver:
                        # Start b43legacy
                        self.log.write(_("Modprobe b43legacy"), 'broadcom.installBroadcom', 'debug')
                        os.system('modprobe b43legacy')
                    elif 'b43' in driver:
                        # Start b43
                        self.log.write(_("Modprobe b43"), 'broadcom.installBroadcom', 'debug')
                        os.system('modprobe b43')
                    else:
                        # Start brcmsmac
                        self.log.write(_("Modprobe brcmsmac"), 'broadcom.installBroadcom', 'debug')
                        os.system('modprobe brcmsmac')

                self.log.write(_("Done installing Broadcom drivers"), 'broadcom.installBroadcom', 'info')
            else:
                self.log.write(_("No Broadcom chip set found"), 'broadcom.installBroadcom', 'error')

        except Exception, detail:
            self.log.write(detail, 'broadcom.installBroadcom', 'exception')

    # Remove the broadcom drivers
    def removeBroadcom(self, driver):
        try:
            if driver != '':
                self.log.write(_("Purge driver: %(drv)s") % { "drv": driver }, 'broadcom.removeBroadcom', 'info')
                cmdPurge = 'apt-get -y --force-yes purge %s' % driver
                self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')

                # Remove blacklist file
                if os.path.exists(blacklistPath):
                    self.log.write(_("Remove : %(file)s") % { "file": blacklistPath }, 'broadcom.removeBroadcom', 'debug')
                    os.remove(blacklistPath)

                self.log.write(_("Done removing Broadcom drivers"), 'broadcom.removeBroadcom', 'info')

        except Exception, detail:
            self.log.write(detail, 'broadcom.removeBroadcom', 'exception')
