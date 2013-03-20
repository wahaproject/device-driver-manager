#!/usr/bin/env python

import functions
from execcmd import ExecCmd
from xorg import XorgConf

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'intel', 'via', 'broadcom', 'pae']


class Intel():

    def __init__(self, distribution, loggerObject, graphicsCard, additionalDrivers=True):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.xc = XorgConf(self.log)
        # Intel manufacturerID = 8086
        self.graphicsCard = graphicsCard
        self.drivers = []

        # Test (00:02.0 VGA compatible controller [0300]: Intel Corporation Atom Processor D4xx/D5xx/N4xx/N5xx Integrated Graphics Controller [8086:a011])
        #self.graphicsCard = [['Intel Corporation Atom Processor D4xx/D5xx/N4xx/N5xx Integrated Graphics Controller', '8086', 'a011']]

        if self.graphicsCard:
            self.drivers.append('xserver-xorg-video-intel')
            if additionalDrivers:
                self.drivers.append('xserver-xorg-video-fbdev')
                self.drivers.append('xserver-xorg-video-vesa')

    # Called from drivers.py: Check for Intel
    def getIntel(self):
        # Check for Intel cards
        hwList = []
        self.log.write('Intel card found: %s' % self.graphicsCard[0], 'ati.getATI', 'info')
        for drv in self.drivers:
            status = functions.getPackageStatus(drv)
            version = functions.getPackageVersion(drv, True)
            description = self.getDriverDescription(drv)
            if status != packageStatus[2]:
                self.log.write('Intel driver found: %s (%s)' % (drv, status), 'intel.getIntel', 'info')
                hwList.append([self.graphicsCard[0], hwCodes[2], status, drv, version, description])
            else:
                self.log.write('Driver not installable: %s' % drv, 'intel.getIntel', 'warning')

        return hwList

    # Called from drivers.py: install the Intel drivers
    def installIntel(self, driver):
        try:
            module = self.xc.getModuleForDriver(hwCodes[2], driver)

            # Install driver if not already installed
            if not functions.isPackageInstalled(driver):
                # Install the appropriate drivers
                self.log.write('Install driver: %s' % driver, 'intel.installIntel', 'info')
                self.ec.run('apt-get -y --force-yes install %s' % driver)

            # Configure xorg.conf
            self.log.write('Found module for driver %s: %s' % (driver, module), 'intel.installIntel', 'debug')
            if module != '':
                self.log.write('Switch to module: %s' % module, 'intel.installIntel', 'info')
                self.xc.setModule('Device', 0, module)

            self.log.write('Driver installed: %s' % driver, 'intel.installIntel', 'info')

        except Exception, detail:
            self.log.write(detail, 'intel.installIntel', 'exception')

    # Called from drivers.py: remove the Intel drivers and revert to radeon
    def removeIntel(self, driver):
        try:
            self.log.write('Remove package: %s' % driver, 'intel.removeIntel', 'debug')
            cmdPurge = 'apt-get -y --force-yes purge ' + driver
            self.ec.run(cmdPurge)
            self.ec.run('apt-get -y --force-yes autoremove')

            # Be sure to have at least vesa
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-vesa')

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write('Driver removed: %s' % driver, 'intel.removeIntel', 'info')

        except Exception, detail:
            self.log.write(detail, 'intel.removeIntel', 'exception')

    def getDriverDescription(self, driver):
        description = ''
        if 'intel' in driver:
            description = 'Intel display driver'
        elif 'fbdev' in driver:
            description = 'Framebuffer display driver'
        elif 'vesa' in driver:
            description = 'Vesa display driver'
        else:
            description = functions.getPackageDescription(driver)
        return description
