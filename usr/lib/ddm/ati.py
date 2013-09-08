#!/usr/bin/env python

import os
import re
import functions
import gettext
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']
# fglrx and fglrx-driver only supports the HD series from 5000 and up
# http://support.amd.com/us/kbarticles/Pages/RN_LN_CAT13-2_Beta.aspx
atiStartSerie = 5000

# i18n
gettext.install("ddm", "/usr/share/locale")


class ATI():

    def __init__(self, distribution, loggerObject, videoCards, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # ATI manufacturerID = 1002
        self.videoCards = videoCards
        self.drivers = []
        self.atiCard = []
        self.isHybrid = False
        self.kernelRelease = functions.getKernelRelease()

        # This should not be listed: 00:01.0 VGA compatible controller [0300]: Advanced Micro Devices [AMD] nee ATI Device [1002:9992]
        #self.videoCards = [['Advanced Micro Devices [AMD] nee ATI Device', '1002', '9992']]

        # This should be listed: 01:00.0 VGA compatible controller [0300]: Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series] [1002:68e0]
        #self.videoCards = [['Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series]', '1002', '68e0']]

        #Hybrid card
        #00:02.0 VGA compatible controller [0300]: Intel Corporation 3rd Gen Core processor Graphics Controller [8086:0166] (rev 09)
        #01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Mars [Radeon HD 8730M] [1002:6601]

        if self.videoCards:
            # Save ATI card information
            for card in self.videoCards:
                if card[1] == '1002':
                    self.atiCard = card
                elif card[1] == '8086':
                    self.isHybrid = True

            if self.distribution == 'debian':
                # Add Debian driver
                self.drivers.append('fglrx-driver')
            else:
                # Ubuntu
                self.drivers.append('fglrx')

            # Additional drivers
            if additionalDrivers:
                if self.isHybrid:
                    self.drivers.append('xserver-xorg-video-intel')
                self.drivers.append('xserver-xorg-video-radeon')
                self.drivers.append('xserver-xorg-video-fbdev')
                self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for ATI
    def getATI(self, hwCode):
        # Check for ATI cards
        hwList = []
        if self.atiCard:
            self.log.write(_("ATI card found: %(card)s") % { "card": self.atiCard[0] }, 'ati.getATI', 'info')
            # Get the ATI chip set serie
            atiSerieMatch = re.search('HD\W(\d*)', self.atiCard[0])
            if atiSerieMatch:
                atiSerie = atiSerieMatch.group(1)
                self.log.write(_("ATI chip serie found: %(serie)s") % { "serie": atiSerie }, 'ati.getATI', 'info')
                intSerie = functions.strToNumber(atiSerie)
                # Only add series from atiStartSerie
                if intSerie >= atiStartSerie:
                    for drv in self.drivers:
                        status = functions.getPackageStatus(drv)
                        version = functions.getPackageVersion(drv, True)
                        description = self.getDriverDescription(drv)
                        if status != packageStatus[2]:
                            self.log.write(_("ATI driver found: %(drv)s (%(status)s)") % ({ "drv": drv, "status": status }), 'ati.getATI', 'info')
                            hwList.append([self.atiCard[0], hwCode, status, drv, version, description])
                        else:
                            self.log.write(_("Driver not installable: %(drv)s") % { "drv": drv }, 'ati.getATI', 'warning')
                else:
                    self.log.write(_("ATI chip serie not supported: %(serie)d") % { "serie": intSerie }, 'ati.getATI', 'warning')
            else:
                self.log.write(_("No driver found for: %(card)s (%(man)s:%(serie)s)") % { "card": self.atiCard[0], "man": self.atiCard[1], "serie": self.atiCard[2] }, 'ati.getATI', 'warning')

        return hwList

    # Called from drivers.py: install the ATI drivers
    def installATI(self, driver, hwCode):
        try:
            isConfigured = False
            module = self.xc.getModuleForDriver(hwCode, driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write(_("Install driver: %(drv)s") % { "drv": driver }, 'ati.installATI', 'info')
                packages = self.getAdditionalPackages(driver)
                self.installATIDriver(packages)
                # Configure ATI
                if module == 'fglrx':
                    self.log.write(_("Configure ATI..."), 'ati.installATI', 'debug')
                    #self.ec.run('aticonfig --adapter=all --initial -f')
                    self.ec.run('aticonfig --initial -f')
                    isConfigured = True

            if not isConfigured:
                # Configure xorg.conf
                self.log.write(_("Found module for driver %(drv)s: %(module)s") % { "drv": driver, "module": module }, 'ati.installATI', 'debug')
                if module != '':
                    self.log.write(_("Switch to module: %(module)s") % { "module": module }, 'ati.installATI', 'info')
                    if module == 'fglrx':
                        self.ec.run('aticonfig --initial -f')
                    else:
                        self.xc.setModule('Device', 0, module)

            self.log.write(_("Driver installed: %(drv)s") % { "drv": driver }, 'ati.installATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.installATI', 'exception')

    # Called from drivers.py: remove the ATI drivers and revert to radeon
    def removeATI(self, driver, hwCode):
        try:
            # Preseed answers for some packages
            self.preseedATIPackages('purge')

            self.log.write(_("Removing ATI drivers"), 'ati.removeATI', 'info')
            packages = self.getAdditionalPackages(driver)
            for package in packages:
                self.log.write(_("Remove package: %(package)s") % { "package": package[0] }, 'ati.removeATI', 'debug')
                cmdPurge = "apt-get -y --force-yes purge %s" % package[0]
                self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have all open drivers available
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-radeon xserver-xorg-video-ati xserver-xorg-video-fbedev xserver-xorg-video-vesa libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write(_("Driver removed: %(drv)s") % { "drv": driver }, 'ati.removeATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.removeATI', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'fglrx' in driver:
            description = _("ATI display driver")
        elif 'intel' in driver:
            description = _("Intel display driver")
        elif 'radeon' in driver:
            description = _("Radeon display driver")
        elif 'fbdev' in driver:
            description = _("Framebuffer display driver")
        elif 'vesa' in driver:
            description = _("Vesa display driver")
        else:
            description = functions.getPackageDescription(driver)
        return description

    # Get additional packages
    # The second value in the list is a numerical value:
    # 0 = Need to install, but removal before reinstallation is not needed
    # 1 = Need to install and removal is needed before reinstallation
    # 2 = Optional install
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getKernelPackages()
        drvList.append([linHeader[1], 0])
        # Common packages
        if self.distribution == 'debian':
            if 'fglrx' in driver:
                drvList.append(['build-essential', 0])
                drvList.append(['module-assistant', 0])
                drvList.append([driver, 1])
                drvList.append(['fglrx-modules-dkms', 1])
                drvList.append(['libgl1-fglrx-glx', 1])
                drvList.append(['glx-alternative-fglrx', 0])
                drvList.append(['fglrx-control', 1])
                drvList.append(['ia32-libs', 2])
                if 'amd64' in self.kernelRelease:
                    drvList.append(['libgl1-fglrx-glx:i386', 2])
            else:
                # Radeon, fbdev, vesa
                drvList.append([driver, 1])
        else:
            drvList.append([driver, 1])
            if 'fglrx' in driver:
                drvList.append(['fglrx-amdcccle', 1])
        return drvList

    # Install the given packages
    def installATIDriver(self, packageList):
        try:
            # Remove certain packages before installing the drivers
            for package in packageList:
                if package[1] == 1:
                    if functions.isPackageInstalled(package[0]):
                        self.log.write(_("Remove package: %(package)s") % { "package": package[0] }, 'ati.installATIDriver', 'debug')
                        self.ec.run("apt-get -y --force-yes remove %s" % package[0])

            # Preseed answers for some packages
            self.preseedATIPackages('install')

            # Install the packages
            installString = ''
            notInRepo = ''
            for package in packageList:
                chkStatus = functions.getPackageStatus(package[0])
                if chkStatus != packageStatus[2]:
                    installString += ' ' + package[0]
                elif package[1] != 2:
                    notInRepo += ', ' + package[0]

            if notInRepo == '':
                self.ec.run('apt-get -y --force-yes install' + installString)
            else:
                self.log.write(_("Install aborted: not in repository: %(repo)s") % { "repo": notInRepo[2:] }, 'ati.installATIDriver', 'error')

        except Exception, detail:
            self.log.write(detail, 'ati.installATIDriver', 'exception')

    def preseedATIPackages(self, action):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep fglrx > debconf-fglrx.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            debConfList.append('libfglrx fglrx-driver/check-for-unsupported-gpu boolean false')
            debConfList.append('fglrx-driver fglrx-driver/check-xorg-conf-on-removal boolean false')
            debConfList.append('libfglrx fglrx-driver/install-even-if-unsupported-gpu-exists boolean false')
            debConfList.append('fglrx-driver fglrx-driver/removed-but-enabled-in-xorg-conf note ')
            debConfList.append('fglrx-driver fglrx-driver/needs-xorg-conf-to-enable note ')

            # Add each line to the debconf database
            for line in debConfList:
                os.system("echo \"%s\" | debconf-set-selections" % line)

            # Install or remove the packages
            self.ec.run("apt-get -y --force-yes %s libfglrx fglrx-driver" % action)
