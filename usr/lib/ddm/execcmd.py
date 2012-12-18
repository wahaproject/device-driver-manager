#!/usr/bin/env python

import sys
import subprocess


# Class to execute a command and return the output in an array
class ExecCmd(object):

    def __init__(self, loggerObject):
        self.log = loggerObject

    def run(self, cmd, realTime=True, defaultMessage=''):
        self.log.write('Command to execute: %s' % cmd, 'execcmd.run', 'debug')

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lstOut = []
        while True:
            # Strip the line, also from null spaces (strip() only strips white spaces)
            line = p.stdout.readline().strip().strip("\0")
            if line == '' and p.poll() is not None:
                break

            if line != '':
                lstOut.append(line)
                if realTime:
                    sys.stdout.flush()
                    self.log.write(line, 'execcmd.run', 'info')

        return lstOut
