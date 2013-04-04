#!/usr/bin/env python

# Class to handle configuration files
# Example:
# [SectionName]
# OptionName = OptionValue

import os
import ConfigParser


class Config():
    def __init__(self, filePath):
        firstChr = filePath[:1]
        if firstChr == '.' or firstChr != '/':
            # Assume only file name
            curDir = os.path.dirname(os.path.realpath(__file__))
            filePath = os.path.join(curDir, filePath)
        else:
            curDir = os.path.dirname(filePath)

        self.curDir = curDir
        self.filePath = filePath
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read([self.filePath])

    def getSections(self):
        return self.parser.sections()

    def doesSectionExist(self, section):
        found = False
        for s in self.getSections():
            if s == section:
                found = True
                break
        return found

    def removeSection(self, section):
        self.parser.remove_section(section)
        f = open(self.filePath, "w")
        self.parser.write(f)
        f.close()

    def getOptions(self, section):
        options = []
        if self.doesSectionExist(section):
            options = self.parser.items(section)
        return options

    def removeOption(self, section, option):
        self.parser.remove_option(section, option)
        f = open(self.filePath, "w")
        self.parser.write(f)
        f.close()

    def getValue(self, section, option):
        value = ''
        try:
            value = self.parser.getint(section, option)
        except ValueError:
            val = self.parser.get(section, option)
            if '\\n' in val:
                valueList = val.split('\\n')
                for v in valueList:
                    value += v + '\n'
            else:
                value = val
        return value

    def setValue(self, section, option, value):
        success = True
        value = str(value)
        try:
            if not os.path.exists(self.curDir):
                os.makedirs(self.curDir)

            if not os.path.exists(self.filePath):
                f = open(self.filePath, "w")
                f.write("")
                f.close()

            if not self.doesSectionExist(section):
                # Create section first
                self.parser.add_section(section)

            self.parser.set(section, option, value)
            f = open(self.filePath, "w")
            self.parser.write(f)
            f.close()

        except Exception:
            success = False
        return success
