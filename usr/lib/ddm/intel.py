#!/usr/bin/env python
#-*- coding: utf-8 -*-

import functions
import gettext
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']

# i18n
gettext.install("ddm", "/usr/share/locale")


class Intel():

    def __init__(self, distribution, loggerObject, videoCards, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # Intel manufacturerID = 8086
        self.videoCards = videoCards
        self.drivers = []
        self.intelCard = []

        # Test (00:02.0 VGA compatible controller [0300]: Intel Corporation Atom Processor D4xx/D5xx/N4xx/N5xx Integrated Graphics Controller [8086:a011])
        #self.videoCards = [['Intel Corporation Atom Processor D4xx/D5xx/N4xx/N5xx Integrated Graphics Controller', '8086', 'a011']]

        if self.videoCards:
            # Save Intel card information
            for card in self.videoCards:
                if card[1] == '8086':
                    self.intelCard = card
                    break

            self.drivers.append('xserver-xorg-video-intel')
            if additionalDrivers:
                self.drivers.append('xserver-xorg-video-fbdev')
                self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for Intel
    def getIntel(self):
        # Check for Intel cards
        hwList = []
        if self.intelCard:
            self.log.write(_("Intel card found: %(card)s") % { "card": self.intelCard[0] }, 'ati.getATI', 'info')
            for drv in self.drivers:
                status = functions.getPackageStatus(drv)
                version = functions.getPackageVersion(drv, True)
                description = self.getDriverDescription(drv)
                if status != packageStatus[2]:
                    self.log.write(_("Intel driver found: %(drv)s (%(status)s)") % { "drv": drv, "status": status }, 'intel.getIntel', 'info')
                    hwList.append([self.intelCard[0], hwCodes[4], status, drv, version, description])
                else:
                    self.log.write(_("Driver not installable: %(drv)s") % { "drv": drv }, 'intel.getIntel', 'warning')

        return hwList

    # Called from drivers.py: install the Intel drivers
    def installIntel(self, driver):
        try:
            #module = self.xc.getModuleForDriver(hwCodes[4], driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write(_("Install driver: %(drv)s") % { "drv": driver }, 'intel.installIntel', 'info')
                self.ec.run('apt-get -y --force-yes install %s' % driver)

            # Configure xorg.conf
            #self.log.write("Found module for driver %(drv)s: %(module)s" % { "drv": driver, "module": module }, 'intel.installIntel', 'debug')
            #if module != '':
                #self.log.write(_("Switch to module: %(module)s") % { "module": module }, 'intel.installIntel', 'info')
                #self.xc.setModule('Device', 0, module)

            self.log.write(_("Driver installed: %(drv)s") % { "drv": driver }, 'intel.installIntel', 'info')

        except Exception, detail:
            self.log.write(detail, 'intel.installIntel', 'exception')

    # Called from drivers.py: remove the Intel drivers and revert to radeon
    def removeIntel(self, driver):
        try:
            self.log.write("Remove package: %(drv)s" % { "drv": driver }, 'intel.removeIntel', 'debug')
            cmdPurge = 'apt-get -y --force-yes purge ' + driver
            self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have at least vesa
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write(_("Driver removed: %(drv)s") % { "drv": driver }, 'intel.removeIntel', 'info')

        except Exception, detail:
            self.log.write(detail, 'intel.removeIntel', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'intel' in driver:
            description = _("Intel display driver")
        elif 'fbdev' in driver:
            description = _("Framebuffer display driver")
        elif 'vesa' in driver:
            description = _("Vesa display driver")
        else:
            description = functions.getPackageDescription(driver)
        return description
