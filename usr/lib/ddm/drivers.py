#!/usr/bin/env python

import threading
from nvidia import Nvidia
from ati import ATI
from intel import Intel
from via import Via
from broadcom import Broadcom
from pae import PAE

hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'intel', 'via', 'nvidia_intel', 'ati_intel']


# Class to check for supported drivers
class DriverGet(threading.Thread):
    def __init__(self, distribution, loggerObject, hwCode, queue, graphicCards=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.log.write('Initialize DriverGet', 'drivers.DriverGet', 'debug')
        self.distribution = distribution
        self.hwCode = hwCode
        self.queue = queue
        self.graphicCards = graphicCards

    # This will only check for Nvidia, ATI, Broadcom and PAE
    def run(self):
        hwList = []

        if self.hwCode == hwCodes[0] or self.hwCode == hwCodes[6]:
            nv = Nvidia(self.distribution, self.log, self.graphicCards)
            hwList = nv.getNvidia(self.hwCode)
        elif self.hwCode == hwCodes[1] or self.hwCode == hwCodes[7]:
            ati = ATI(self.distribution, self.log, self.graphicCards)
            hwList = ati.getATI(self.hwCode)
        elif self.hwCode == hwCodes[2]:
            bc = Broadcom(self.distribution, self.log)
            hwList = bc.getBroadcom()
        elif self.hwCode == hwCodes[3]:
            pae = PAE(self.distribution, self.log)
            hwList = pae.getPae()
        elif self.hwCode == hwCodes[4]:
            intel = Intel(self.distribution, self.log, self.graphicCards)
            hwList = intel.getIntel()
        elif self.hwCode == hwCodes[5]:
            via = Via(self.distribution, self.log, self.graphicCards)
            hwList = via.getVia()

        self.queue.put(hwList)
        self.queue.task_done()


# Driver install class needs threading
class DriverInstall(threading.Thread):
    def __init__(self, distribution, loggerObject, hwCode, driver='', graphicCards=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.hwCode = hwCode
        self.driver = driver
        self.log.write('Initialize DriverInstall', 'drivers.DriverInstall', 'debug')
        self.distribution = distribution
        self.graphicCards = graphicCards

    # Install hardware drivers for given hardware code and driver
    def run(self):
        if self.hwCode == hwCodes[0] or self.hwCode == hwCodes[6]:
            nv = Nvidia(self.distribution, self.log, self.graphicCards)
            nv.installNvidia(self.driver, self.hwCode)
        elif self.hwCode == hwCodes[1] or self.hwCode == hwCodes[7]:
            ati = ATI(self.distribution, self.log, self.graphicCards)
            ati.installATI(self.driver, self.hwCode)
        elif self.hwCode == hwCodes[2]:
            bc = Broadcom(self.distribution, self.log)
            bc.installBroadcom(self.driver)
        elif self.hwCode == hwCodes[3]:
            pae = PAE(self.distribution, self.log)
            pae.installPAE()
        elif self.hwCode == hwCodes[4]:
            intel = Intel(self.distribution, self.log, self.graphicCards)
            intel.installIntel(self.driver)
        elif self.hwCode == hwCodes[5]:
            via = Via(self.distribution, self.log, self.graphicCards)
            via.installVia(self.driver)


# Driver install class needs threading
class DriverRemove(threading.Thread):
    def __init__(self, distribution, loggerObject, hwCode, driver='', graphicCards=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.hwCode = hwCode
        self.driver = driver
        self.log.write('Initialize DriverRemove', 'drivers.DriverRemove', 'debug')
        self.distribution = distribution
        self.graphicCards = graphicCards

    # Install hardware drivers for given hardware codes (hwCodes)
    def run(self):
        # Instantiate driver classes
        if self.hwCode == hwCodes[0] or self.hwCode == hwCodes[6]:
            nv = Nvidia(self.distribution, self.log, self.graphicCards)
            nv.removeNvidia(self.driver, self.hwCode)
        elif self.hwCode == hwCodes[1] or self.hwCode == hwCodes[7]:
            ati = ATI(self.distribution, self.log, self.graphicCards)
            ati.removeATI(self.driver, self.hwCode)
        elif self.hwCode == hwCodes[2]:
            bc = Broadcom(self.distribution, self.log)
            bc.removeBroadcom(self.driver)
        elif self.hwCode == hwCodes[3]:
            pae = PAE(self.distribution, self.log)
            pae.removePAE()
        elif self.hwCode == hwCodes[4]:
            intel = Intel(self.distribution, self.log, self.graphicCards)
            intel.removeIntel(self.driver)
        elif self.hwCode == hwCodes[5]:
            via = Via(self.distribution, self.log, self.graphicCards)
            via.removeVia(self.driver)
