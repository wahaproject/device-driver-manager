#!/usr/bin/env python -u
#-*- coding: utf-8 -*-

# python -u tells python not to buffer stdout

import sys
import subprocess


# Class to execute a command and return the output in an array
class ExecCmd(object):

    def __init__(self, loggerObject):
        self.log = loggerObject

    def run(self, cmd, realTime=True, defaultMessage=''):
        if self.log:
            self.log.write("Command to execute: %(cmd)s" % { "cmd": cmd }, 'execcmd.run', 'debug')

        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lstOut = []
        while True:
            line = p.stdout.readline()
            if not line:
                break
            # Strip the line, also from null spaces (strip() only strips white spaces)
            line = line.decode('utf-8').strip().strip("\0")
            #if line == '' and p.poll() is not None:
            lstOut.append(line)
            if realTime:
                if self.log:
                    self.log.write(line, 'execcmd.run', 'info')
                else:
                    print line
            sys.stdout.flush()

        return lstOut
