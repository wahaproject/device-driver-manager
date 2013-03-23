#!/usr/bin/env python

try:
    import os
    import sys
    import pygtk
    pygtk.require('2.0')
    import gtk
    import threading
    import Queue
    import glib
    import functions
    import string
    import getopt
    import webbrowser
    from config import Config
    from treeview import TreeViewHandler
    from xorg import XorgConf
    from broadcom import Broadcom
    from pae import PAE
    from drivers import DriverGet, DriverInstall
    from dialogs import QuestionDialog, MessageDialogSave
    from logger import Logger
except Exception, detail:
    print detail
    sys.exit(1)

hwCodes = ['nvidia', 'ati', 'intel', 'via', 'broadcom', 'pae']
menuItems = ['graphics', 'wireless', 'kernel']


#class for the main window
class DDM:

    def __init__(self):
        self.scriptDir = os.path.dirname(os.path.realpath(__file__))
        # Load window and widgets
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(self.scriptDir, '../../share/ddm/ddm.glade'))
        self.window = self.builder.get_object('ddmWindow')
        self.lblTitle = self.builder.get_object('lblTitle')
        self.lblCardName = self.builder.get_object('lblCardName')
        self.lblTitleActivatedDriver = self.builder.get_object('lblTitleActivatedDriver')
        self.lblAlternativeDriversTitle = self.builder.get_object('lblAlternativeDriversTitle')
        self.swDrivers = self.builder.get_object('swDrivers')
        self.tvDrivers = self.builder.get_object('tvDrivers')
        self.statusbar = self.builder.get_object('statusbar')
        self.ebTitle = self.builder.get_object('ebTitle')
        self.lblDDM = self.builder.get_object('lblDDM')
        self.ebMenu = self.builder.get_object('ebMenu')
        self.ebMenuGraphics = self.builder.get_object('ebMenuGraphics')
        self.lblMenuGraphics = self.builder.get_object('lblMenuGraphics')
        self.ebMenuWireless = self.builder.get_object('ebMenuWireless')
        self.lblMenuWireless = self.builder.get_object('lblMenuWireless')
        self.ebMenuKernel = self.builder.get_object('ebMenuKernel')
        self.lblMenuKernel = self.builder.get_object('lblMenuKernel')
        self.imgManufacturer = self.builder.get_object('imgManufacturer')
        self.lblActivatedDriver = self.builder.get_object('lblActivatedDriver')
        self.ebManufacturer = self.builder.get_object('ebManufacturer')
        self.spinner = self.builder.get_object('spinner')

        # Read from config file
        self.cfg = Config('ddm.conf')
        self.clrTitleFg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'title_fg'))
        self.clrTitleBg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'title_bg'))
        self.clrMenuSelect = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_select'))
        self.clrMenuHover = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_hover'))
        self.clrMenuBg = gtk.gdk.Color(self.cfg.getValue('COLORS', 'menu_bg'))
        self.urlNvidia = self.cfg.getValue('MANUFACTURERS_SITES', 'nvidia')
        self.urlAmd = self.cfg.getValue('MANUFACTURERS_SITES', 'amd')
        self.urlBroadcom = self.cfg.getValue('MANUFACTURERS_SITES', 'broadcom')
        self.urlPae = self.cfg.getValue('MANUFACTURERS_SITES', 'pae')
        self.urlIntel = self.cfg.getValue('MANUFACTURERS_SITES', 'intel')
        self.urlVia = self.cfg.getValue('MANUFACTURERS_SITES', 'via')

        self.selectedMenuItem = None
        self.mediaDir = '/usr/share/ddm'
        self.lockFile = '/var/lib/dpkg/lock'
        self.debug = False
        self.install = False
        self.isHybrid = False
        self.logPath = ''
        self.kernelRelease = None
        self.queue = Queue.Queue()

        self.nvidiaDrivers = []
        self.atiDrivers = []
        self.intelDrivers = []
        self.viaDrivers = []
        self.broadcomDrivers = []
        self.paePackage = []
        self.usedDrivers = []
        self.graphDependencies = []
        self.manufacturerModules = []
        self.currentHwCode = None
        self.prevDriverPath = None

        # Add events
        signals = {
            'on_ebMenuGraphics_button_release_event': self.showMenuGraphics,
            'on_ebMenuGraphics_enter_notify_event': self.changeMenuGraphics,
            'on_ebMenuGraphics_leave_notify_event': self.cleanMenu,
            'on_ebMenuWireless_button_release_event': self.showMenuWireless,
            'on_ebMenuWireless_enter_notify_event': self.changeMenuWireless,
            'on_ebMenuWireless_leave_notify_event': self.cleanMenu,
            'on_ebMenuKernel_button_release_event': self.showMenuKernel,
            'on_ebMenuKernel_enter_notify_event': self.changeMenuKernel,
            'on_ebMenuKernel_leave_notify_event': self.cleanMenu,
            'on_ebManufacturer_button_release_event': self.showManufacturerSite,
            'on_ddmWindow_destroy': self.destroy
        }
        self.builder.connect_signals(signals)

        self.window.show()

    # ===============================================
    # Menu section functions
    # ===============================================

    def cleanMenu(self, widget, event):
        self.changeMenuBackground(self.selectedMenuItem)

    def changeMenuGraphics(self, widget, event):
        self.changeMenuBackground(menuItems[0])

    def changeMenuWireless(self, widget, event):
        self.changeMenuBackground(menuItems[1])

    def changeMenuKernel(self, widget, event):
        self.changeMenuBackground(menuItems[2])

    def changeMenuBackground(self, menuItem, select=False):
        ebs = []
        ebs.append([menuItems[0], self.ebMenuGraphics])
        ebs.append([menuItems[1], self.ebMenuWireless])
        ebs.append([menuItems[2], self.ebMenuKernel])
        for eb in ebs:
            if eb[0] == menuItem:
                if select:
                    self.selectedMenuItem = menuItem
                    eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuSelect)
                else:
                    if eb[0] != self.selectedMenuItem:
                        eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuHover)
            else:
                if eb[0] != self.selectedMenuItem or select:
                    eb[1].modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)

    def showMenuGraphics(self, widget=None, event=None):
        if self.selectedMenuItem != menuItems[0]:
            self.changeMenuBackground(menuItems[0], True)
            self.lblTitle.set_text(self.lblMenuGraphics.get_text())
            self.clearDriverSection('No supported graphics card found')

            if self.nvidiaDrivers:
                self.currentHwCode = hwCodes[0]
                self.manufacturerModules = self.xc.getModules(hwCodes[0])
                self.loadDriverSection(self.nvidiaDrivers)
            elif self.atiDrivers:
                self.currentHwCode = hwCodes[1]
                self.manufacturerModules = self.xc.getModules(hwCodes[1])
                self.loadDriverSection(self.atiDrivers)
                if self.intelDrivers:
                    self.isHybrid = True
            elif self.intelDrivers:
                self.currentHwCode = hwCodes[2]
                self.manufacturerModules = self.xc.getModules(hwCodes[2])
                self.loadDriverSection(self.intelDrivers)
            elif self.viaDrivers:
                self.currentHwCode = hwCodes[3]
                self.manufacturerModules = self.xc.getModules(hwCodes[3])
                self.loadDriverSection(self.viaDrivers)

    def showMenuWireless(self, widget=None, event=None):
        if self.selectedMenuItem != menuItems[1]:
            self.changeMenuBackground(menuItems[1], True)
            self.lblTitle.set_text(self.lblMenuWireless.get_text())
            self.clearDriverSection('No supported wireless chipset found')

            if self.broadcomDrivers:
                self.currentHwCode = hwCodes[4]
                self.loadDriverSection(self.broadcomDrivers)

    def showMenuKernel(self, widget=None, event=None):
        if self.selectedMenuItem != menuItems[2]:
            self.changeMenuBackground(menuItems[2], True)
            self.lblTitle.set_text(self.lblMenuKernel.get_text())
            msg = 'PAE already installed'
            if 'amd64' in self.kernelRelease:
                msg = 'PAE support only for 32-bit systems'
            self.clearDriverSection(msg)

            if self.paePackage:
                self.currentHwCode = hwCodes[5]
                self.loadDriverSection(self.paePackage)

    # ===============================================
    # Driver section functions
    # ===============================================

    # Clear the driver section
    def clearDriverSection(self, notFoundMessage=None):
        self.currentHwCode = None
        if notFoundMessage:
            self.lblCardName.set_text(notFoundMessage)

        # Hide driver section items
        self.lblTitleActivatedDriver.hide()
        self.lblAlternativeDriversTitle.hide()
        self.swDrivers.hide()

        imgPath = os.path.join(self.mediaDir, 'empty.png')
        if os.path.exists(imgPath):
            self.imgManufacturer.set_from_file(imgPath)
        self.lblActivatedDriver.set_text('')
        self.tvHandler.clearTreeView()

    # Show driver information of the selected menu topic
    def loadDriverSection(self, driverList):
        # self.hw, hwCode, status, drv, version, description
        contentList = []
        rowCnt = -1

        # Show driver section items
        self.lblTitleActivatedDriver.show()
        self.lblAlternativeDriversTitle.show()
        self.swDrivers.show()

        # Add column names for driver treeview
        row = ['Activate', 'Driver', 'Version', 'Description', 'hwCode']
        contentList.append(row)

        i = 0
        cardSet = False
        actDrvFound = False
        for item in driverList:
            activate = False

            recommended = ''
            if self.manufacturerModules and i == 0:
                recommended = ' (recommended)'
            i += 1

            # Check drivers with currently loaded drivers
            if self.usedDrivers:
                for drv in self.usedDrivers:
                    # Check if a driver from the repositories is used
                    if drv[0] == menuItems[0]:
                        for dep in self.graphDependencies:
                            if dep == item[3]:
                                drv[1] = dep
                                break

                    self.log.write('Check loaded driver / available driver: %s / %s' % (drv[1], item[3]), 'ddm.loadDriverSection', 'debug')
                    if drv[1] == item[3] and drv[0] == self.selectedMenuItem:
                        self.log.write('Select current driver in list: %s' % drv[1], 'ddm.loadDriverSection', 'debug')
                        self.lblActivatedDriver.set_text('%s %s%s' % (item[3], item[4], recommended))
                        activate = True
                        actDrvFound = True
                        rowCnt += 1
                        break

            # Write driver info to screen
            if not cardSet:
                cardSet = True
                self.lblCardName.set_text(item[0])
                imgPath = os.path.join(self.mediaDir, self.currentHwCode + '.png')
                if os.path.exists(imgPath):
                    self.log.write('Manufacturer image path: %s' % imgPath, 'ddm.loadDriverSection', 'debug')
                    self.imgManufacturer.show()
                    self.imgManufacturer.set_from_file(imgPath)
                else:
                    self.imgManufacturer.hide()

            # Fill driver list
            # Activate, Driver, Version, Description, hwCode
            row = [activate, item[3], item[4], item[5] + recommended, item[1]]
            contentList.append(row)

        # In case driver is loaded, but not by a repository package, just show the loaded driver
        self.tvDrivers.set_sensitive(True)
        if not actDrvFound and self.usedDrivers:
            for drv in self.usedDrivers:
                if drv[0] == self.selectedMenuItem:
                    self.tvDrivers.set_sensitive(False)
                    title = 'Unknown driver'
                    self.log.write('%s: %s' % (title, drv[1]), 'ddm.loadDriverSection', 'warning')
                    self.lblActivatedDriver.set_text(drv[1])
                    msg = 'Unknown driver found.\n\nPlease remove before installing drivers with DDM.'
                    MessageDialogSave(title, msg, gtk.MESSAGE_WARNING, self.window).show()

        # Fill treeview with drivers
        #fillTreeview(contentList, columnTypesList, columnHideList=[-1], setCursor=0, setCursorWeight=400, firstItemIsColName=False, appendToExisting=False, appendToTop=False)
        columnTypesList = ['bool', 'str', 'str', 'str', 'str']
        self.tvHandler.fillTreeview(contentList, columnTypesList, [4], rowCnt, 600, True, False, False)
        self.prevDriverPath = rowCnt

    # Open the manufacturer site in the default browser
    def showManufacturerSite(self, widget, event):
        url = ''
        if self.currentHwCode == hwCodes[0]:
            url = self.urlNvidia
        elif self.currentHwCode == hwCodes[1]:
            url = self.urlAmd
        elif self.currentHwCode == hwCodes[2]:
            url = self.urlIntel
        elif self.currentHwCode == hwCodes[3]:
            url = self.urlVia
        elif self.currentHwCode == hwCodes[4]:
            url = self.urlBroadcom
        elif self.currentHwCode == hwCodes[5]:
            url = self.urlPae
        if url != '':
            webbrowser.open(url)

    # This method is fired by the TreeView.checkbox-toggled event
    def driverCheckBoxToggled(self, obj, path, colNr, toggleValue):
        path = int(path)
        model = self.tvDrivers.get_model()
        itr = model.get_iter(path)
        driver = model[itr][1]
        hwCode = model[itr][4]

        if self.prevDriverPath != path or toggleValue:
            # Only one toggle box can be selected (or none)
            self.tvHandler.treeviewToggleAll([0], False, 1, driver)

            # Ask user for activation and install/switch
            qd = QuestionDialog('Driver activation', 'Are you sure you want to install the following driver:\n\n%s' % driver, self.window)
            answer = qd.show()
            if answer:
                # Check if /var/dpkg/lock has been locked by another process
                if functions.isFileLocked(self.lockFile):
                    MessageDialogSave('Locked', 'Could not get lock on %s.\n\nClose any programs locking the file and try again.' % self.lockFile, gtk.MESSAGE_WARNING, self.window).show()
                else:
                    cardsDone = []
                    for card in self.cards:
                        if hwCode not in cardsDone:
                            self.log.write('Driver to install: %s' % driver, 'ddm.driverCheckBoxToggled', 'debug')
                            # Install in separate thread
                            self.prevDriverPath = path
                            self.toggleGuiElements(True)
                            t = DriverInstall(self.distribution, self.log, hwCode, driver, card, self.isHybrid)
                            t.daemon = True
                            t.start()
                            # Run spinner as long as the thread is alive
                            #self.log.write('Check every 5 miliseconds if thread is still active', 'ddm.driverCheckBoxToggled', 'debug')
                            glib.timeout_add(5, self.checkInstallThread, driver)
                            cardsDone.append(hwCode)
            else:
                # Toggle previous row as well when rows has changed
                #if self.prevDriverPath != path:
                self.tvHandler.treeviewToggleRows([0], [self.prevDriverPath])
                self.tvHandler.treeviewToggleRows([0], [path])
        else:
            # At least one driver must be selected (if available)
            # Toggle current row back on to prevent that no driver is selected
            self.tvHandler.treeviewToggleRows([0], [path])

    def checkGetInfoThread(self):
        #print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            return True

        # Thread is done
        # Get the data from the queue
        hwList = self.queue.get()

        if hwList:
            if hwList[0][1] == hwCodes[0]:
                self.nvidiaDrivers = hwList
            elif hwList[0][1] == hwCodes[1]:
                self.atiDrivers = hwList
            elif hwList[0][1] == hwCodes[2]:
                self.intelDrivers = hwList
            elif hwList[0][1] == hwCodes[3]:
                self.viaDrivers = hwList
            elif hwList[0][1] == hwCodes[4]:
                self.broadcomDrivers = hwList
            elif hwList[0][1] == hwCodes[5]:
                self.paePackage = hwList

        # Select the appropriate menu when all threads are done
        if threading.active_count() == 1:
            self.selectedMenuItem = None
            if self.nvidiaDrivers or self.atiDrivers or self.intelDrivers or self.viaDrivers:
                self.showMenuGraphics()
            elif self.broadcomDrivers:
                self.showMenuWireless()
            elif self.paePackage:
                self.showMenuKernel()
            else:
                self.showMenuGraphics()

        self.toggleGuiElements(False)

        return False

    def checkInstallThread(self, driver):
        #print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            return True

        # Thread is done
        self.toggleGuiElements(False)
        qd = QuestionDialog('Driver installed', 'Driver installed: %s\n\nDrivers will be used on next boot.\nDo you want to reboot now?' % driver, self.window)
        answer = qd.show()
        if answer:
            # Reboot
            os.system('reboot')
        return False

    def toggleGuiElements(self, startThread):
        if startThread:
            self.tvDrivers.set_sensitive(False)
            self.spinner.show()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.hide()
            self.tvDrivers.set_sensitive(True)
            # Show version number in status bar
            functions.pushMessage(self.statusbar, self.version)

    # Make thread safe by queue
    def getHardwareInfo(self, hwCode, graphicsCard=None):
        self.toggleGuiElements(True)

        # Start the thread
        t = DriverGet(self.distribution, self.log, hwCode, self.queue, graphicsCard)
        t.daemon = True
        t.start()
        self.queue.join()
        # Run spinner as long as the thread is alive
        #self.log.write('Check every 5 miliseconds if thread is still active', 'ddm.getHardwareInfo', 'debug')
        glib.timeout_add(5, self.checkGetInfoThread)

    # ===============================================
    # Main
    # ===============================================

    def main(self, argv):
        # Handle arguments
        try:
            opts, args = getopt.getopt(argv, 'ic:dfl:', ['install', 'codes=', 'debug', 'force', 'log='])
        except getopt.GetoptError:
            print 'Arguments cannot be parsed: ' + str(argv)
            sys.exit(1)

        for opt, arg in opts:
            if opt in ('-d', '--debug'):
                self.debug = True
            elif opt in ('-i', '--install'):
                self.install = True
            elif opt in ('-c', '--codes'):
                self.hwPreSelectList = arg.split(',')
            elif opt in ('-l', '--log'):
                self.logPath = arg

        # Initialize logging
        if self.debug:
            if not self.logPath:
                self.logPath = 'ddm.log'
        self.log = Logger(self.logPath, 'debug', True, self.statusbar, self.window)
        functions.log = self.log

        # Check if self.lockFile is locked by another process
        if functions.isFileLocked(self.lockFile):
            MessageDialogSave('Locked', 'Could not get lock on %s.\n\nClose any programs locking the file and restart DDM.' % self.lockFile, gtk.MESSAGE_WARNING, self.window).show()
            sys.exit(2)

        # Initiate the treeview handler and connect the custom toggle event with driverCheckBoxToggled
        self.tvHandler = TreeViewHandler(self.log, self.tvDrivers)
        self.tvHandler.connect('checkbox-toggled', self.driverCheckBoxToggled)

        # Set background and forground colors
        self.ebTitle.modify_bg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblMenuGraphics.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblMenuWireless.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblMenuKernel.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblTitle.modify_fg(gtk.STATE_NORMAL, self.clrTitleBg)
        self.lblDDM.modify_fg(gtk.STATE_NORMAL, self.clrTitleFg)
        self.ebMenu.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)
        self.ebMenuGraphics.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)
        self.ebMenuWireless.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)
        self.ebMenuKernel.modify_bg(gtk.STATE_NORMAL, self.clrMenuBg)

        # Change cursor
        self.ebMenuGraphics.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))
        self.ebMenuWireless.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))
        self.ebMenuKernel.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))
        self.ebManufacturer.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))

        # Get currently loaded drivers
        self.version = functions.getPackageVersion('ddm')
        self.distribution = functions.getDistribution()
        self.xc = XorgConf(self.log)
        self.bc = Broadcom(self.distribution, self.log)
        self.pae = PAE(self.distribution, self.log)
        usedGraphDriver = self.xc.getUsedDriver()
        usedWirelessDrivers = self.bc.getUsedDriver()
        usedPaeHeader = self.pae.getInstalledPaePackage()
        if usedGraphDriver:
            self.usedDrivers.append([menuItems[0], usedGraphDriver])
            # Get a list with packages that have a dependency with usedGraphDriver
            loadedPackages = functions.getPackagesWithFile('%s_drv' % usedGraphDriver.lower())
            for package in loadedPackages:
                self.graphDependencies.append(package)
                depList = functions.getPackageDependencies(package, True)
                for dep in depList:
                    if dep != package:
                        self.graphDependencies.append(dep)
        if usedWirelessDrivers:
            self.usedDrivers.append([menuItems[1], usedWirelessDrivers])
        if usedPaeHeader:
            self.usedDrivers.append([menuItems[2], usedPaeHeader])
        self.log.write('Used drivers: %s' % self.usedDrivers, 'ddm.main', 'debug')

        # Show initial window while getting hardware info
        msg = 'Checking your hardware...'
        self.log.write(msg, 'ddm.main', 'info')
        functions.pushMessage(self.statusbar, msg)
        self.showMenuGraphics()
        self.clearDriverSection()
        self.lblCardName.set_text('')
        functions.repaintGui()

        # Get the appropriate driver info
        self.kernelRelease = functions.getKernelRelease()

        # Get hardware info
        # Graphics
        self.cards = functions.getGraphicsCards()
        # ATI test: must not show
        # self.cards = [['Advanced Micro Devices [AMD] nee ATI Device', '1002', '9992']]
        # ATI test: show
        # self.cards = [['Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series]', '1002', '68e0']]
        cardsDone = []
        for card in self.cards:
            if card[1] == '10de' and hwCodes[0] not in cardsDone:
                # Nvidia
                self.getHardwareInfo(hwCodes[0], card)
                cardsDone.append(hwCodes[0])
            if card[1] == '1002' and hwCodes[1] not in cardsDone:
                # ATI
                self.getHardwareInfo(hwCodes[1], card)
                cardsDone.append(hwCodes[1])
            if card[1] == '8086' and hwCodes[2] not in cardsDone:
                # Intel
                self.getHardwareInfo(hwCodes[2], card)
                cardsDone.append(hwCodes[2])
            if card[1] == '1106' and hwCodes[3] not in cardsDone:
                # Via
                self.getHardwareInfo(hwCodes[3], card)
                cardsDone.append(hwCodes[3])
        # Wireless
        self.getHardwareInfo(hwCodes[4])
        # PAE
        self.getHardwareInfo(hwCodes[5])

        # Start automatic install
        if self.install:
            self.log.write('Start automatic driver install', 'ddm.main', 'info')
            # TODO - automatic (recommended) driver install

        # Show window and keep it on top of other windows
        #self.window.set_keep_above(True)
        gtk.main()

    def destroy(self, widget, data=None):
        # Close the app
        gtk.main_quit()


if __name__ == '__main__':
    # Flush print when it's called
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # Create an instance of our GTK application
    app = DDM()

    # Very dirty: replace the : back again with -
    # before passing the arguments
    args = sys.argv[1:]
    for i in range(len(args)):
        args[i] = string.replace(args[i], ':', '-')
    app.main(args)
