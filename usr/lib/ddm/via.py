#!/usr/bin/env python

import functions
import gettext
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']

# i18n
gettext.install("ddm", "/usr/share/locale")


class Via():

    def __init__(self, distribution, loggerObject, videoCards, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # Intel manufacturerID = 1106
        self.videoCards = videoCards
        self.drivers = []
        self.viaCard = []

        # Test (01:00.0 VGA compatible controller [0300]: VIA Technologies, Inc KM400/KN400/P4P800 [S3 Unichrome][1106:7205] (rev 01))
        #self.videoCards = [['VIA Technologies, Inc KM400/KN400/P4P800 [S3 Unichrome]', '1106', '7205']]

        if self.videoCards:
            # Save Via card information
            for card in self.videoCards:
                if card[1] == '1106':
                    self.viaCard = card
                    break

            self.drivers.append('xserver-xorg-video-openchrome')
            if additionalDrivers:
                self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for Via
    def getVia(self):
        # Check for Via cards
        hwList = []
        if self.viaCard:
            self.log.write(_("Via card found: %(card)s") % { "card": self.viaCard[0] }, 'via.getATI', 'info')
            for drv in self.drivers:
                status = functions.getPackageStatus(drv)
                version = functions.getPackageVersion(drv, True)
                description = self.getDriverDescription(drv)
                if status != packageStatus[2]:
                    self.log.write(_("Via driver found: %(drv)s (%(status)s)") % { "drv": drv, "status": status }, 'via.getVia', 'info')
                    hwList.append([self.viaCard[0], hwCodes[5], status, drv, version, description])
                else:
                    self.log.write(_("Driver not installable: %(drv)s") % { "drv": drv }, 'via.getVia', 'warning')

        return hwList

    # Called from drivers.py: install the Via drivers
    def installVia(self, driver):
        try:
            module = self.xc.getModuleForDriver(hwCodes[5], driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write(_("Install driver: %(drv)s") % { "drv": driver }, 'via.installVia', 'info')
                self.ec.run('apt-get -y --force-yes install %s' % driver)

            # Configure xorg.conf
            self.log.write(_("Found module for driver %(drv)s: %(module)s") % { "drv": driver, "module": module }, 'via.installVia', 'debug')
            if module != '':
                self.log.write(_("Switch to module: %(module)s") % { "module": module }, 'via.installVia', 'info')
                self.xc.setModule('Device', 0, module)

            self.log.write(_("Driver installed: %(drv)s") % { "drv": driver }, 'via.installVia', 'info')

        except Exception, detail:
            self.log.write(detail, 'via.installVia', 'exception')

    # Called from drivers.py: remove the Via drivers and revert to radeon
    def removeVia(self, driver):
        try:
            self.log.write(_("Remove package: %(drv)s") % { "drv": driver }, 'via.removeVia', 'debug')
            cmdPurge = 'apt-get -y --force-yes purge %s' % driver
            self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have at least vesa
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write(_("Driver removed: %(drv)s") % { "drv": driver }, 'via.removeVia', 'info')

        except Exception, detail:
            self.log.write(detail, 'via.removeVia', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'chrome' in driver:
            description = _("Chrome display driver")
        elif 'fbdev' in driver:
            description = _("Framebuffer display driver")
        elif 'vesa' in driver:
            description = _("Vesa display driver")
        else:
            description = functions.getPackageDescription(driver)
        return description
