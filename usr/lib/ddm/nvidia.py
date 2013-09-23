#!/usr/bin/env python

import os
import functions
import gettext
from nvidiadetector import NvidiaDetection
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']
blacklistPath = '/etc/modprobe.d/blacklist-nouveau.conf'

# i18n
gettext.install("ddm", "/usr/share/locale")


class Nvidia():
    def __init__(self, distribution, loggerObject, videoCards, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # Intel manufacturerID = 10de
        self.videoCards = videoCards
        self.drivers = []
        self.nvidiaCard = []
        self.isBumblebee = False
        self.kernelRelease = functions.getKernelRelease()

        # Test (01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GT218 [GeForce G210M] [10de:0a74] (rev ff))
        # self.videoCards = [['NVIDIA Corporation GT218 [GeForce G210M]', '10de', '0a74']]

        #Hybrid
        #00:02.0 VGA compatible controller [0300]: Intel Corporation 2nd Generation Core Processor Family Integrated Graphics Controller [8086:0126] (rev 09)
        #01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GF108M [GeForce GT 540M] [10de:0df4] (rev ff)
        #sudo apt-get install -y bumblebee bumblebee-nvidia primus
        #sudo adduser bumblebee christopher

        if self.videoCards:
            # Save Nvidia card information
            for card in self.videoCards:
                if card[1] == '10de':
                    self.nvidiaCard = card
                elif card[1] == '8086':
                    self.isBumblebee = True

            # Install nvidia-detect if it isn't installed already
            if self.distribution == 'debian':
                if self.isBumblebee:
                    self.drivers = ['bumblebee-nvidia']
                    if additionalDrivers:
                        self.drivers.append('xserver-xorg-video-intel')

                if functions.getPackageVersion('nvidia-detect') == '':
                    self.log.write(_("Update apt"), 'nvidia.init', 'info')
                    self.ec.run('apt-get update')
                if not functions.isPackageInstalled('nvidia-detect'):
                    self.log.write(_("Install nvidia-detect"), 'nvidia.init', 'info')
                    self.ec.run('apt-get -y --force-yes install nvidia-detect')

                nvDrv = self.ec.run("nvidia-detect | grep nvidia- | tr -d ' '")
                if nvDrv:
                    self.drivers.append(nvDrv[0])

                if 'not found' in self.drivers:
                    self.log.write(_("Cannot install nvidia-detect: abort"), 'nvidia.init', 'critical')
                    exit()

                # Add additional drivers
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
    def getNvidia(self, hwCode):
        hwList = []
        if self.nvidiaCard:
            self.log.write(_("Nvidia card found: %(card)s") % { "card": self.nvidiaCard[0] }, 'nvidia.getNvidia', 'info')
            for drv in self.drivers:
                # This is a temporary hack, needed for the experimental nvidia-detect
                # Remove the following if statement when nvidia-glx-legacy-304xx hits testing
                if drv == "nvidia-glx-legacy-304xx":
                    drv = "nvidia-glx"
                status = functions.getPackageStatus(drv)
                version = functions.getPackageVersion(drv, True)
                description = self.getDriverDescription(drv)
                if status != packageStatus[2]:
                    self.log.write(_("Nvidia driver found: %(drv)s (%(status)s)") % { "drv": drv, "status": status }, 'nvidia.getNvidia', 'info')
                    hwList.append([self.nvidiaCard[0], hwCode, status, drv, version, description])
                else:
                    self.log.write(_("Driver not installable: %(drv)s") % { "drv": drv }, 'nvidia.getNvidia', 'warning')

        return hwList

    # Called from drivers.py: install the Nvidia drivers
    def installNvidia(self, driver, hwCode):
        try:
            isConfigured = False
            module = self.xc.getModuleForDriver(hwCode, driver)
            version = functions.getPackageVersion(driver, True).split('-')[0]

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write(_("Install driver: %(drv)s") % { "drv": driver }, 'nvidia.installNvidia', 'info')
                packages = self.getAdditionalPackages(driver)
                self.installNvidiaPackages(packages, version)
                # Configure nvidia for Debian
                if self.distribution == 'debian' and module == 'nvidia':
                    if self.isBumblebee:
                        userName = functions.getUserLoginName()
                        self.ec.run("adduser bumblebee %s" % userName)
                    else:
                        self.log.write(_("Configure Nvidia..."), 'nvidia.installNvidia', 'debug')
                        self.ec.run('nvidia-xconfig')
                        self.xc.blacklistModule('nouveau')

                    isConfigured = True

            if not isConfigured:
                # Configure xorg.conf
                self.log.write(_("Found module for driver %(drv)s: %(module)s") % { "drv": driver, "module": module }, 'nvidia.installNvidia', 'debug')
                if module != '':
                    self.log.write(_("Switch to module: %(module)s") % { "module": module }, 'nvidia.installNvidia', 'info')
                    if module == 'nvidia':
                        if self.distribution == 'debian':
                            self.ec.run('nvidia-xconfig')
                        self.xc.blacklistModule('nouveau')
                    else:
                        self.xc.setModule('Device', 0, module)
                        # Remove blacklist from nouveau
                        self.xc.blacklistModule('nouveau', False)

            self.log.write(_("Driver installed: %(drv)s") % { "drv": driver }, 'nvidia.installNvidia', 'info')

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidia', 'exception')

    # Called from drivers.py: remove the Nvidia drivers and revert to Nouveau
    def removeNvidia(self, driver, hwCode):
        try:
            # Preseed answers for some packages
            version = functions.getPackageVersion(driver, True).split('-')[0]
            self.preseedNvidiaPackages('purge', version)

            self.log.write(_("Removing Nvidia drivers"), 'nvidia.removeNvidia', 'info')
            packages = self.getAdditionalPackages(driver)
            for package in packages:
                self.log.write(_("Remove package: %(package)s") % { "package": package[0] }, 'nvidia.removeNvidia', 'debug')
                cmdPurge = 'apt-get -y --force-yes purge ' + package[0]
                self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have all open drivers available
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa xserver-xorg-video-fbdev xserver-xorg-video-nouveau')

            # Remove blacklist Nouveau
            self.xc.blacklistModule('nouveau', False)

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write(_("Driver removed: %(drv)s") % { "drv": driver }, 'nvidia.removeNvidia', 'info')

        except Exception, detail:
            self.log.write(detail, 'nvidia.removeNvidia', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'nvidia' in driver:
            description = _("Nvidia display driver")
        elif 'intel' in driver:
            description = _("Intel display driver")
        elif 'nouveau' in driver:
            description = _("Nouveau display driver")
        elif 'fbdev' in driver:
            description = _("Framebuffer display driver")
        elif 'vesa' in driver:
            description = _("Vesa display driver")
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
                    self.log.write(_("Is package installed: %(package)s") % { "package": package[0] }, 'nvidia.installNvidiaPackages', 'debug')
                    drvChkCmd = 'aptitude search %s | grep ^i | wc -l' % package[0]
                    drvChk = self.ec.run(drvChkCmd, False)
                    if functions.strToNumber(drvChk[0]) > 0:
                        # Build remove packages string
                        removePackages += ' ' + package[0]

            # Remove these packages before installation
            if removePackages != '':
                self.log.write(_("Remove drivers before reinstallation: %(drv)s") % { "drv": removePackages }, 'nvidia.installNvidiaPackages', 'debug')
                nvDrvRemCmd = 'apt-get -y --force-yes remove%s' % removePackages
                self.ec.run(nvDrvRemCmd)

            # Preseed answers for some packages
            self.preseedNvidiaPackages('install', version)

            # Install the packages
            self.log.write(_("Install drivers: %(drv)s") % { "drv": installPackages }, 'nvidia.installNvidiaPackages', 'debug')
            nvDrvInstCmd = 'apt-get -y --force-yes install%s' % installPackages
            self.ec.run(nvDrvInstCmd)

        except Exception, detail:
            self.log.write(detail, 'nvidia.installNvidiaPackages', 'exception')

    # Get additional packages
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getKernelPackages()
        drvList.append([linHeader[1], 0])
        # Distribution specific packages
        if self.distribution == 'debian':
            if 'nvidia-' in driver:
                drvList.append(['build-essential', 0])
                drvList.append([driver, 1])
                # This needs to change when 304 goes legacy
                if driver == 'nvidia-glx':
                    drvList.append(['nvidia-kernel-dkms', 1])
                    if 'amd64' in self.kernelRelease:
                        drvList.append(['ia32-libs', 2])
                elif driver == 'bumblebee-nvidia':
                    drvList.append(['nvidia-kernel-dkms', 1])
                    drvList.append(['bumblebee', 1])
                    drvList.append(['primus', 1])
                    drvList.append(['primus-libs-ia32', 2])
                elif driver == 'nvidia-glx-legacy-96xx':
                    drvList.append(['nvidia-kernel-legacy-96xx-dkms', 1])
                    if 'amd64' in self.kernelRelease:
                        drvList.append(['ia32-libs', 2])
                elif driver == 'nvidia-glx-legacy-173xx':
                    drvList.append(['nvidia-kernel-legacy-173xx-dkms', 1])
                    if 'amd64' in self.kernelRelease:
                        drvList.append(['ia32-libs', 2])
                # Uncomment the following if statement when nvidia-glx-legacy-304xx hits testing
                #elif driver == 'nvidia-glx-legacy-304xx':
                #    drvList.append(['nvidia-kernel-legacy-304xx-dkms', 1])
                #    drvList.append(['ia32-libs', 2])
                if 'amd64' in self.kernelRelease:
                    drvList.append(['libgl1-nvidia-glx:i386', 2])
                drvList.append(['nvidia-xconfig', 0])
                drvList.append(['nvidia-settings', 0])

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
