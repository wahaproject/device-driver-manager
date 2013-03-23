#!/usr/bin/env python

import os
import functions
from nvidiadetector import NvidiaDetection
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via']
blacklistPath = '/etc/modprobe.d/blacklist-nouveau.conf'


class Nvidia():
    def __init__(self, distribution, loggerObject, graphicsCard, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # Intel manufacturerID = 10de
        self.graphicsCard = graphicsCard
        self.drivers = []

        # Test (01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GT218 [GeForce G210M] [10de:0a74] (rev ff))
        # self.graphicsCard = [['NVIDIA Corporation GT218 [GeForce G210M]', '10de', '0a74']]

        if self.graphicsCard:
            # Install nvidia-detect if it isn't installed already
            if self.distribution == 'debian':
                if functions.getPackageVersion('nvidia-detect') == '':
                    self.log.write('Update apt', 'nvidia.init', 'info')
                    self.ec.run('apt-get update')
                if not functions.isPackageInstalled('nvidia-detect'):
                    self.log.write('Install nvidia-detect', 'nvidia.init', 'info')
                    self.ec.run('apt-get -y --force-yes install nvidia-detect')
                self.drivers = self.ec.run("nvidia-detect | grep nvidia- | tr -d ' '")
                if 'not found' in self.drivers:
                    self.log.write('Cannot install nvidia-detect: abort', 'nvidia.init', 'critical')
                    exit()

                # Add additional drivers
                if additionalDrivers:
                    self.drivers.append('xserver-xorg-video-nouveau')
                    self.drivers.append('xserver-xorg-video-fbdev')
                    self.drivers.append('xserver-xorg-video-vesa')
            else:
                # Ubuntu - use jockey code
                nd = NvidiaDetection()
                drivers = nd.selectDrivers()
                for driver in drivers:
                    self.drivers.append(driver)

                # Add additional drivers
                if additionalDrivers:
                    self.drivers.append('xserver-xorg-video-nouveau')
                    self.drivers.append('xserver-xorg-video-fbdev')
                    self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for Nvidia
    def getNvidia(self):
        hwList = []
        if self.drivers and self.graphicsCard:
            for drv in self.drivers:
                status = functions.getPackageStatus(drv)
                version = functions.getPackageVersion(drv, True)
                description = self.getDriverDescription(drv)
                if status != packageStatus[2]:
                    self.log.write('Nvidia driver found: %s (%s)' % (drv, status), 'nvidia.getNvidia', 'info')
                    hwList.append([self.graphicsCard[0], hwCodes[0], status, drv, version, description])
                else:
                    self.log.write('Driver not installable: %s' % drv, 'nvidia.getNvidia', 'warning')
        else:
            self.log.write('No driver found for: %s (%s:%s)' % (self.graphicsCard[0], self.graphicsCard[1], self.graphicsCard[2]), 'nvidia.getNvidia', 'warning')

        return hwList

    # Called from drivers.py: install the Nvidia drivers
    def installNvidia(self, driver):
        try:
            isConfigured = False
            module = self.xc.getModuleForDriver(hwCodes[0], driver)
            version = functions.getPackageVersion(driver, True).split('-')[0]

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write('Install driver: %s' % driver, 'nvidia.installNvidia', 'info')
                packages = self.getAdditionalPackages(driver)
                self.installNvidiaPackages(packages, version)
                # Configure nvidia for Debian
                if self.distribution == 'debian' and module == 'nvidia':
                    self.log.write('Configure Nvidia...', 'nvidia.installNvidia', 'debug')
                    self.ec.run('nvidia-xconfig')
                    self.xc.blacklistModule('nouveau')
                    isConfigured = True

            if not isConfigured:
                # Configure xorg.conf
                self.log.write('Found module for driver %s: %s' % (driver, module), 'nvidia.installNvidia', 'debug')
                if module != '':
                    self.log.write('Switch to module: %s' % module, 'nvidia.installNvidia', 'info')
                    if module == 'nvidia':
                        if self.distribution == 'debian':
                            self.ec.run('nvidia-xconfig')
                        self.xc.blacklistModule('nouveau')
                    else:
                        self.xc.setModule('Device', 0, module)
                        # Remove blacklist from nouveau
                        self.xc.blacklistModule('nouveau', False)

            self.log.write('Driver installed: %s' % driver, 'nvidia.installNvidia', 'info')

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidia', 'exception')

    # Called from drivers.py: remove the Nvidia drivers and revert to Nouveau
    def removeNvidia(self, driver):
        try:
            # Preseed answers for some packages
            version = functions.getPackageVersion(driver, True).split('-')[0]
            self.preseedNvidiaPackages('purge', version)

            self.log.write('Removing Nvidia drivers', 'nvidia.removeNvidia', 'info')
            packages = self.getAdditionalPackages(driver)
            for package in packages:
                self.log.write('Remove package: %s' % package[0], 'nvidia.removeNvidia', 'debug')
                cmdPurge = 'apt-get -y --force-yes purge ' + package[0]
                self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have all open drivers available
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa xserver-xorg-video-fbdev xserver-xorg-video-nouveau')

            # Remove blacklist Nouveau
            self.xc.blacklistModule('nouveau', False)

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write('Driver removed: %s' % driver, 'nvidia.removeNvidia', 'info')

        except Exception, detail:
            self.log.write(detail, 'nvidia.removeNvidia', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'nvidia' in driver:
            description = 'Nvidia display driver'
        elif 'nouveau' in driver:
            description = 'Nouveau display driver'
        elif 'fbdev' in driver:
            description = 'Framebuffer display driver'
        elif 'vesa' in driver:
            description = 'Vesa display driver'
        else:
            description = functions.getPackageDescription(driver)
        return description

    # Install the given packages
    def installNvidiaPackages(self, packageList, version):
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
                    self.log.write('Is package installed: %s' % package[0], 'nvidia.installNvidiaPackages', 'debug')
                    drvChkCmd = 'aptitude search %s | grep ^i | wc -l' % package[0]
                    drvChk = self.ec.run(drvChkCmd, False)
                    if functions.strToNumber(drvChk[0]) > 0:
                        # Build remove packages string
                        removePackages += ' ' + package[0]

            # Remove these packages before installation
            if removePackages != '':
                self.log.write('Remove drivers before reinstallation: %s' % removePackages, 'nvidia.installNvidiaPackages', 'debug')
                nvDrvRemCmd = 'apt-get -y --force-yes remove%s' % removePackages
                self.ec.run(nvDrvRemCmd)

            # Preseed answers for some packages
            self.preseedNvidiaPackages('install', version)

            # Install the packages
            self.log.write('Install drivers: %s' % installPackages, 'nvidia.installNvidiaPackages', 'debug')
            nvDrvInstCmd = 'apt-get -y --force-yes install%s' % installPackages
            self.ec.run(nvDrvInstCmd)

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidiaPackages', 'exception')

    # Get additional packages
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getLinuxHeadersAndImage()
        drvList.append([linHeader[0], 0])
        # Distribution specific packages
        if self.distribution == 'debian':
            if 'nvidia-' in driver:
                drvList.append(['build-essential', 0])
                drvList.append([driver, 1])
                if driver == 'nvidia-glx':
                    drvList.append(['nvidia-kernel-dkms', 1])
                elif driver == 'nvidia-glx-legacy-96xx':
                    drvList.append(['nvidia-kernel-legacy-96xx-dkms', 1])
                elif driver == 'nvidia-glx-legacy-173xx':
                    drvList.append(['nvidia-kernel-legacy-173xx-dkms', 1])
                drvList.append(['nvidia-xconfig', 0])
                drvList.append(['nvidia-settings', 0])

                # 64-bit only?
                if functions.getPackageStatus('fglrx-glx-ia32') == 'notinstalled':
                    drvList.append(['nvidia-glx-ia32', 2])
            else:
                # Nouveau, fbdev, vesa
                drvList.append([driver, 1])
        else:
            # TODO - Ubuntu packages
            drvList.append([driver, 1])
            if 'updates' in driver:
                drvList.append(['nvidia-settings-updates', 0])
            elif 'experimental-304' in driver:
                drvList.append(['nvidia-settings-experimental-304', 0])
            elif 'experimental-310' in driver:
                drvList.append(['nvidia-settings-experimental-310', 0])
            else:
                drvList.append(['nvidia-settings', 0])

        return drvList

    def preseedNvidiaPackages(self, action, version):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep nvidia > debconf-nvidia.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            #debConfList.append('nvidia-support nvidia-support/warn-nouveau-module-loaded error ')
            debConfList.append('nvidia-support nvidia-support/check-xorg-conf-on-removal boolean false')
            debConfList.append('nvidia-support nvidia-support/check-running-module-version boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/delete-nvidia-installer boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/remove-conflicting-libraries boolean true')
            #debConfList.append('nvidia-support nvidia-support/removed-but-enabled-in-xorg-conf error ')
            #debConfList.append('nvidia-support nvidia-support/warn-mismatching-module-version error ')
            debConfList.append('nvidia-support nvidia-support/last-mismatching-module-version string ' + version)
            debConfList.append('nvidia-support nvidia-support/needs-xorg-conf-to-enable note ')
            debConfList.append('nvidia-support nvidia-support/create-nvidia-conf boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/uninstall-nvidia-installer boolean true')

            # Add each line to the debconf database
            for line in debConfList:
                os.system('echo "' + line + '" | debconf-set-selections')

            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes %s nvidia-support nvidia-installer-cleanup' % action)
