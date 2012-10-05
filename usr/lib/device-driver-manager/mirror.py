#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = [ 'installed', 'notinstalled', 'uninstallable' ]
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']

class Mirror():
    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.currentMirror = ''
        self.bestMirror = ''
        
    def getFastestMirror(self):
        mirList = []
        if self.distribution == 'debian':
            # Check if mint-debian-mirrors is installed
            if functions.getPackageStatus('mint-debian-mirrors') == packageStatus[0]:
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
        mirList.append(['Fastest mirror: ' + self.bestMirror, hwCodes[4], status])
        
        return mirList

    def installMirror(self):
        pass
        
    def removeMirror(self):
        pass
