#!/usr/bin/env python

import os
import functions
import nvidia_gpus
from execcmd import ExecCmd

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']
blacklistPath = '/etc/modprobe.d/blacklist-nouveau.conf'

# Nvidia drivers
# driver serial nr, debian driver, ubuntu driver
drivers = [
[304, 'nvidia-glx', 'nvidia-current'],
[173, 'nvidia-glx-legacy-173xx', 'nvidia-173'],
[96, 'nvidia-glx-legacy-96xx', 'nvidia-96']
]


class Nvidia():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        # Get gpu info
        self.gpu = []
        manPciId = functions.getGraphicsCardManufacturerPciId()
        if manPciId:
            if manPciId[0].lower() == '10de':  # Nividia manufacturer id
                self.gpu = nvidia_gpus.checkNvidiaID(manPciId[1])
                self.log.write('Nvidia driver info: ' + str(self.gpu), 'nvidia.init', 'debug')

    # Called from drivers.py: Check for Nvidia
    def getNvidia(self):
        hwList = []
        if self.gpu:
            # Get driver for Nvidia
            self.log.write('Get the appropriate Nvidia driver', 'nvidia.getNvidia', 'info')
            drv = self.getDriver()
            if drv != '':
                self.log.write('Nvidia driver to install: ' + drv, 'nvidia.getNvidia', 'info')
                status = functions.getPackageStatus(drv)
                self.log.write('Package status: ' + status, 'nvidia.getNvidia', 'debug')
                hwList.append([self.gpu[1], hwCodes[0], status])
            else:
                self.log.write('No supported driver found for: ' + self.gpu[1], 'nvidia.getNvidia', 'warning')
                hwList.append([self.gpu[1], hwCodes[0], packageStatus[2]])
        else:
            self.log.write('No supported Nvidia card found', 'nvidia.getNvidia', 'debug')

        return hwList

    # Get the driver for the system's Nvidia card
    def getDriver(self):
        try:
            driver = ''
            for drv in drivers:
                if drv[0] == self.gpu[0]:
                    if self.distribution == 'debian':
                        driver = drv[1]
                    else:
                        driver = drv[2]
                    break
            return driver
        except Exception, detail:
            self.log.write(detail, 'nvidia.getDriver', 'exception')

    # Install the given packages
    def installNvidiaDriver(self, packageList):
        try:
            # Remove certain packages before installing the drivers
            for package in packageList:
                if package[1] == 1:
                    if functions.isPackageInstalled(package[0]):
                        self.log.write('Remove package: ' + package[0], 'nvidia.installNvidiaDriver', 'debug')
                        self.ec.run('apt-get -y --force-yes remove ' + package[0])

            # Preseed answers for some packages
            self.preseedNvidiaPackages('install')

            # Install the packages
            for package in packageList:
                if not functions.isPackageInstalled(package[0]):
                    self.log.write('Install package: ' + package[0], 'nvidia.installNvidiaDriver', 'debug')
                    self.ec.run('apt-get -y --force-yes install ' + package[0])

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidiaDriver', 'exception')

    # Get additional packages
    # The second value in the list is a numerical value (True=1, False=0) whether the package must be removed before installation
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getLinuxHeadersAndImage()
        drvList.append([linHeader[0], 0])
        # Distribution specific packages
        if self.distribution == 'debian':
            drvList.append(['build-essential', 0])
            drvList.append([driver, 1])
            if driver == 'nvidia-glx':
                drvList.append(['nvidia-kernel-dkms', 1])
            elif driver == 'nvidia-glx-legacy-96xx':
                drvList.append(['nvidia-kernel-legacy-96xx-dkms', 1])
            elif driver == 'nvidia-glx-legacy-173xx':
                drvList.append(['nvidia-kernel-legacy-173xx-dkms', 1])
            drvList.append(['nvidia-xconfig', 0])
            drvList.append(['nvidia-glx-ia32', 0])
        else:
            drvList.append([driver, 1])

        # Common packages
        drvList.append(['nvidia-settings', 0])
        return drvList

    # Called from drivers.py: install the Nvidia drivers
    def installNvidia(self):
        try:
            # Get the appropriate drivers for the card
            drv = self.getDriver()
            if drv != '':
                packages = self.getAdditionalPackages(drv)
                self.installNvidiaDriver(packages)
                # Install the appropriate drivers
                if self.distribution == 'debian':
                    # Configure Nvidia
                    self.log.write('Configure Nvidia...', 'nvidia.installNvidia', 'debug')
                    self.ec.run('nvidia-xconfig')

                # Blacklist Nouveau
                self.log.write('Blacklist Nouveau: ' + blacklistPath, 'nvidia.installNvidia', 'debug')
                modFile = open(blacklistPath, 'w')
                modFile.write('blacklist nouveau')
                modFile.close()

                self.log.write('Done installing Nvidia drivers', 'nvidia.installNvidia', 'info')
            else:
                self.log.write('No apprpriate driver found', 'nvidia.installNvidia', 'error')

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidia', 'exception')

    # Called from drivers.py: remove the Nvidia drivers and revert to Nouveau
    def removeNvidia(self):
        try:
            # Preseed answers for some packages
            self.preseedNvidiaPackages('purge')

            self.log.write('Removing Nvidia drivers', 'nvidia.removeNvidia', 'info')
            packages = self.getAdditionalPackages(self.getDriver())
            for package in packages:
                self.log.write('Remove package: ' + package[0], 'nvidia.removeNvidia', 'debug')
                self.ec.run('apt-get -y --force-yes purge ' + package[0])
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-nouveau')

            # Remove blacklist Nouveau
            if os.path.exists(blacklistPath):
                self.log.write('Remove : ' + blacklistPath, 'nvidia.removeNvidia', 'debug')
                os.remove(blacklistPath)

            # Rename xorg.conf
            xorg = '/etc/X11/xorg.conf'
            if os.path.exists(xorg):
                self.log.write('Rename : ' + xorg + ' -> ' + xorg + '.ddm.bak', 'nvidia.removeNvidia', 'debug')
                os.rename(xorg, xorg + '.ddm.bak')

            self.log.write('Done removing Nvidia drivers', 'nvidia.removeNvidia', 'info')

        except Exception, detail:
            self.log.write(detail, 'nvidia.removeNvidia', 'exception')

    def preseedNvidiaPackages(self, action):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep nvidia > debconf-nvidia.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            debConfList.append('nvidia-support nvidia-support/warn-nouveau-module-loaded note ')
            debConfList.append('nvidia-support nvidia-support/check-xorg-conf-on-removal boolean false')
            debConfList.append('nvidia-support nvidia-support/check-running-module-version boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/delete-nvidia-installer boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/remove-conflicting-libraries boolean true')
            debConfList.append('nvidia-support nvidia-support/removed-but-enabled-in-xorg-conf note ')
            debConfList.append('nvidia-support nvidia-support/warn-mismatching-module-version note ')
            debConfList.append('nvidia-support nvidia-support/last-mismatching-module-version string 302.17')
            debConfList.append('nvidia-support nvidia-support/needs-xorg-conf-to-enable note ')
            debConfList.append('nvidia-support nvidia-support/create-nvidia-conf boolean true')
            debConfList.append('nvidia-installer-cleanup nvidia-installer-cleanup/uninstall-nvidia-installer boolean true')

            # Add each line to the debconf database
            for line in debConfList:
                os.system('echo "' + line + '" | debconf-set-selections')

            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes ' + action + ' nvidia-support nvidia-installer-cleanup')
