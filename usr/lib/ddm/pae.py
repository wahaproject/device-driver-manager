#!/usr/bin/env python
#-*- coding: utf-8 -*-

import functions
import gettext
from execcmd import ExecCmd

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']

# i18n
gettext.install("ddm", "/usr/share/locale")


class PAE():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.distributionReleaseNumber = functions.getDistributionReleaseNumber()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.kernelRelease = functions.getKernelRelease()
        self.packages = functions.getKernelPackages(True, 'pae$', '-rt')
        self.installedPackage = None

    # Check the distribution if a PAE check is needed
    def needCheckForPae(self):
        skipPae = False
        # Ubuntu is already PAE enabled from version 12.10 (Quantal) and LM 14 Nadia is based on Quantal: no need to check
        # https://help.ubuntu.com/community/EnablingPAE
        if (self.distribution == 'linuxmint' and self.distributionReleaseNumber >= 14) or (self.distribution == 'ubuntu' and self.distributionReleaseNumber >= 12.10) or 'amd64' in self.kernelRelease:
            self.log.write("Already a PAE system or AMD64", 'pae.needCheckForPae', 'debug')
            skipPae = True
        return skipPae

    # Get the installed PAE linux header package
    def getInstalledPaePackage(self):
        installedPae = None
        if 'pae' in self.kernelRelease:
            linHeaders = 'linux-headers-' + self.kernelRelease
            if functions.isPackageInstalled(linHeaders):
                installedPae = linHeaders
                self.log.write(_("Installed PAE: %(pae)s") % { "pae": installedPae }, 'pae.getInstalledPaePackage', 'info')
        return installedPae

    # Check if the PAE kernel can be installed
    def getPae(self):
        hwList = []
        description = _("Multi-core support for 32-bit systems")
        self.log.write("Distribution: %(dist)s" % { "dist": self.distribution + ' ' + str(self.distributionReleaseNumber) }, 'pae.getPae', 'debug')

        if not self.needCheckForPae():
            # Check the machine hardware
            machine = self.ec.run('uname -m')
            installedPackage = self.getInstalledPaePackage()

            if installedPackage:
                version = functions.getPackageVersion(installedPackage)
                self.log.write(_("Multi-core already installed: %(package)s") % { "package": installedPackage }, 'pae.getPae', 'info')
                hwList.append([_("PAE capable system"), hwCodes[3], packageStatus[0], installedPackage, version, description])
            else:
                self.log.write("Single-core kernel found: %(kernel)s" % { "kernel": self.kernelRelease }, 'pae.getPae', 'debug')

                # Get #CPU's: cat /proc/cpuinfo | grep processor | wc -l
                if machine[0] == 'i686':
                    self.log.write(_("Multi-core system running single-core kernel found"), 'pae.getPae', 'info')
                    # Check package status
                    status = packageStatus[0]
                    if not functions.isPackageInstalled(self.packages[0]):
                        self.log.write(_("PAE not installed"), 'pae.getPae', 'info')
                        status = packageStatus[1]
                        version = functions.getPackageVersion(self.packages[0], True)
                        hwList.append([_("PAE capable system"), hwCodes[3], status, self.packages[0], version, description])

                elif machine[0] == 'x86_64':
                    # You shouldn't get here
                    self.log.write("PAE skipped: 64-bit system", 'pae.getPae', 'debug')
                else:
                    self.log.write(_("PAE kernel cannot be installed: single-core system"), 'pae.getPae', 'warning')

        return hwList

    # Called from drivers.py: install PAE kernel
    def installPAE(self):
        try:
            cmdPae = 'apt-get -y --force-yes install linux-image-686-pae linux-headers-686-pae'
            for package in self.packages:
                cmdPae += ' ' + package
            self.log.write("PAE kernel install command: %(cmd)s" % { "cmd": cmdPae }, 'pae.installPAE', 'debug')
            self.ec.run(cmdPae)

            # Backup and remove xorg.conf
            functions.backupFile('/etc/X11/xorg.conf', True)

            self.log.write(_("Done installing PAE"), 'pae.installPAE', 'info')

        except Exception, detail:
            self.log.write(detail, 'pae.installPAE', 'error')

    # Called from drivers.py: remove the PAE kernel
    # TODO: I don't think this is going to work - test this
    def removePAE(self):
        try:
            kernelRelease = self.ec.run('uname -r')
            if not 'pae' in kernelRelease[0]:
                self.log.write("Not running pae, continue removal", 'pae.removePAE', 'debug')
                for package in self.packages:
                    cmdPurge = 'apt-get -y --force-yes purge linux-image-686-pae linux-headers-686-pae %s' % package
                    self.log.write(_("PAE package to remove: %(package)s") % { "package": package }, 'pae.removePAE', 'info')
                    self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')
                self.log.write(_("Done removing PAE"), 'pae.removePAE', 'info')
            else:
                self.log.write(_("Cannot remove PAE when running PAE"), 'pae.removePAE', 'warning')

        except Exception, detail:
            self.log.write(detail, 'pae.removePAE', 'error')

# Pre-seed ?
## Installatie afbreken na depmod fout?
#linux-image-3.13-1-686-pae linux-image-3.13-1-686-pae/postinst/depmod-error-initrd-3.13-1-686-pae boolean false
## Het verwijderen van de kernel afbreken?
#linux-image-3.13-1-686-pae linux-image-3.13-1-686-pae/prerm/removing-running-kernel-3.13-1-686-pae boolean true
