#!/usr/bin/env python

import sys
import os
import pwd
import logging
import functions
import gtk
from dialogs import MessageDialog

class Logger():

    def __init__(self, logPath='', defaultLogLevel='debug', addLogTime=True, rtObject=None):
        self.logPath = logPath
        if self.logPath != '':
            if self.logPath[:1] != '/':
                homeDir = pwd.getpwuid(os.getuid()).pw_dir
                self.logPath = os.path.join(homeDir, self.logPath)
        self.defaultLevel = getattr(logging, defaultLogLevel.upper())
        self.logTime = addLogTime
        self.rtobject = rtObject
        self.typeString = functions.getTypeString(self.rtobject)
        
        if self.logPath == '':
            # Log only to console
            logging.basicConfig(level=self.defaultLevel, format='%(levelname)-10s%(message)s')
        else:
            # Set basic configuration
            formatStr = '%(name)-30s%(levelname)-10s%(message)s'
            dateFmtStr = None
            if addLogTime:
                formatStr = '%(asctime)s ' + formatStr
                dateFmtStr = '%d-%m-%Y %H:%M:%S'
            
            # Log to file
            logging.basicConfig(filename=self.logPath, level=self.defaultLevel, format=formatStr, datefmt=dateFmtStr)
            
            # Define a Handler which writes INFO messages or higher to the console
            # Debug messages are written to a specified log file
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(levelname)-10s%(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)
    
    # Write message
    def write(self, message, loggerName='log', logLevel='debug'):
        message = str(message).strip()
        if message != '':
            logLevel = logLevel.lower()
            myLogger = logging.getLogger(loggerName)
            if logLevel == 'debug':
                myLogger.debug(message)
            elif logLevel == 'info':
                myLogger.info(message)
                self.rtobjectWrite(message)
            elif logLevel == 'warning':
                myLogger.warning(message)
                self.rtobjectWrite(message)
            elif logLevel == 'error':
                myLogger.error(message)
                #self.rtobjectWrite(message)
                MessageDialog('Error', message, gtk.MESSAGE_ERROR).show()
            elif logLevel == 'critical':
                myLogger.critical(message)
                #self.rtobjectWrite(message)
                MessageDialog('Critical', message, gtk.MESSAGE_ERROR).show()
            elif logLevel == 'exception':
                myLogger.exception(message)
                #self.rtobjectWrite(message)
                MessageDialog('Exception', message, gtk.MESSAGE_ERROR).show()
                
    # Return messge to given object
    def rtobjectWrite(self, message):
        if self.rtobject != None and self.typeString != '':
            if self.typeString == 'gtk.Label':
                self.rtobject.set_text(message)
            elif self.typeString == 'gtk.TreeView':
                functions.appendRowToTreeView(self.rtobject, message, True)
            elif self.typeString == 'gtk.Statusbar':
                functions.pushMessage(self.rtobject, message)
            else:
                # For obvious reasons: do not log this...
                print 'Return object type not implemented: ' + self.typeString


# Test
#log = Logger('myapp.log') # Log file and console
#log = Logger() # Console only
#log.write('Dit is een debug test', 'myapp.gui', 'debug') # Should not end up in console when writing to log file
#log.write('Dit is een info test', 'myapp.gui', 'info')
#log.write('Dit is een warning test', 'myapp.gui', 'warning')
#log.write('Dit is een error test', 'myapp.gui', 'error')