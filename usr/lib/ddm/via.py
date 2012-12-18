#!/usr/bin/env python

import functions
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'intel', 'via', 'broadcom', 'pae']


class Via():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        self.hw = functions.getGraphicsCards('1106')
        self.drivers = []

        # Test (01:00.0 VGA compatible controller [0300]: VIA Technologies, Inc KM400/KN400/P4P800 [S3 Unichrome][1106:7205] (rev 01))
        #self.hw = ['VIA Technologies, Inc KM400/KN400/P4P800 [S3 Unichrome]']

        if self.hw:
            self.drivers.append('xserver-xorg-video-openchrome')
            self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for Via
    def getVia(self):
        # Check for Via cards
        hwList = []
        for card in self.hw:
            self.log.write('Via card found: %s' % card, 'via.getATI', 'info')
            for drv in self.drivers:
                status = functions.getPackageStatus(drv)
                version = functions.getPackageVersion(drv, True)
                description = self.getDriverDescription(drv)
                if status != packageStatus[2]:
                    self.log.write('Via driver found: %s (%s)' % (drv, status), 'via.getVia', 'info')
                    hwList.append([card, hwCodes[3], status, drv, version, description])
                else:
                    self.log.write('Driver not installable: %s' % drv, 'via.getVia', 'warning')

        return hwList

    # Called from drivers.py: install the Via drivers
    def installVia(self, driver):
        try:
            module = self.xc.getModuleForDriver(hwCodes[3], driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write('Install driver: %s' % driver, 'via.installVia', 'info')
                self.ec.run('apt-get -y --force-yes install %s' % driver)

            # Configure xorg.conf
            self.log.write('Found module for driver %s: %s' % (driver, module), 'via.installVia', 'debug')
            if module != '':
                self.log.write('Switch to module: %s' % module, 'via.installVia', 'info')
                self.xc.setModule('Device', 0, module)

            self.log.write('Driver installed: %s' % driver, 'via.installVia', 'info')

        except Exception, detail:
            self.log.write(detail, 'via.installVia', 'exception')

    # Called from drivers.py: remove the Via drivers and revert to radeon
    def removeVia(self, driver):
        try:
            self.log.write('Remove package: %s' % driver, 'via.removeVia', 'debug')
            cmdPurge = 'apt-get -y --force-yes purge %s' % driver
            self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have at least vesa
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write('Driver removed: %s' % driver, 'via.removeVia', 'info')

        except Exception, detail:
            self.log.write(detail, 'via.removeVia', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'chrome' in driver:
            description = 'Chrome display driver'
        elif 'fbdev' in driver:
            description = 'Framebuffer display driver'
        elif 'vesa' in driver:
            description = 'Vesa display driver'
        else:
            description = functions.getPackageDescription(driver)
        return description
