#!/usr/bin/env python

import sys
import subprocess
import re
import functions
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)


# Class to execute a command and return the output in an array
class ExecCmd(object):
    
    def __init__(self, loggerObject):
        self.log = loggerObject
        
    def run(self, cmd, realTime=True, defaultMessage=''):
        self.log.write('Command to execute: ' + cmd, 'execcmd.run', 'debug')

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lstOut = []
        while True:
            line = p.stdout.readline().strip()
            if line == '' and p.poll() != None:
                break
            
            if line != '':
                lstOut.append(line)
                sys.stdout.flush()
                if realTime:
                    self.log.write(line, 'execcmd.run', 'info')
            
        return lstOut
