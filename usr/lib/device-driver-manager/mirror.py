#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']


class Mirror():
    def __init__(self, distribution, loggerObject, currentMirror='', bestMirror=''):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.currentMirror = currentMirror
        self.bestMirror = bestMirror

    def getFastestMirror(self):
        mirList = []
        if self.distribution == 'debian':
            # Check if mint-debian-mirrors is installed
            if functions.isPackageInstalled('mint-debian-mirrors'):
                # Get the mirrors
                cmd = 'mint-choose-debian-mirror --dry-run'
                mirrors = self.ec.run(cmd)
                for mirror in mirrors:
                    # Extract the url
                    urlObj = re.search('http[a-zA-Z0-9:\.\-/]*', mirror)
                    if urlObj:
                        url = urlObj.group()
                        if 'current server' in mirror.lower():
                            self.log.write('Current server: ' + url, 'mirror.getFastestMirror', 'info')
                            self.currentMirror = url
                        elif 'best server' in mirror.lower():
                            self.log.write('Best server: ' + url, 'mirror.getFastestMirror', 'info')
                            self.bestMirror = url
                    else:
                        self.log.write('No mirror URL found', 'mirror.getFastestMirror', 'warning')
            else:
                self.log.write('Cannot detect fastest mirror: mint-debian-mirrors not installed', 'mirror.getFastestMirror', 'warning')
        else:
            # TODO: do this for Ubuntu
            pass

        # Append fastest mirror to list
        status = packageStatus[2]
        if self.bestMirror != '':
            if self.bestMirror == self.currentMirror:
                status = packageStatus[0]
            else:
                status = packageStatus[1]
            mirList.append(['Install the fastest repository mirror', hwCodes[4], status])

        return mirList

    # Let mint-debian-mirrors write the fastest mirror to sources.list
    def installMirror(self):
        cmd = 'mint-choose-debian-mirror --force-fastest'
        self.log.write('Mirror command=' + cmd, 'mirror.installMirror', 'debug')
        self.ec.run(cmd)
        self.log.write('Resynchronizing the package index files from their sources', 'mirror.installMirror', 'info')
        os.system("apt-get update")

    # Restore the sources.list backup file
    def removeMirror(self):
        sourcesFile = '/etc/apt/sources.list'
        bakFile = '/etc/apt/sources.list.bk'
        if os.path.exists(bakFile):
            self.log.write('Restore backup file: ' + bakFile, 'mirror.removeMirror', 'info')
            if os.path.exists(sourcesFile):
                self.ec.run('mv -fv ' + sourcesFile + ' ' + sourcesFile + '.ddm.bk')
            self.ec.run('mv -fv ' + bakFile + ' ' + sourcesFile)
            self.log.write('Resynchronize the package index files from their sources', 'mirror.removeMirror', 'info')
            self.ec.run('apt-get update')
        else:
            self.log.write('Cannot restore sources.list backup file: does not exist', 'mirror.removeMirror', 'warning')
