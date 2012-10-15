#!/usr/bin/env python

try:
    import os
    import sys
    import pygtk
    pygtk.require('2.0')
    import gtk
    import threading
    import glib
    import functions
    import string
    import getopt
    from drivers import DriverCheck, DriverInstall, DriverRemove
    from dialogs import MessageDialog
    from config import Config
    from logger import Logger
except Exception, detail:
    print detail
    sys.exit(1)
    
    
#class for the main window
class DebianDriverManager:

    conf = Config('ddm.conf')
    version = ''
    hwList = []
    hwPreSelectList = []
    install = False
    debug = False
    mediaDir = '/usr/share/device-driver-manager'
    logPath = ''
    paeChecked = False

    def __init__(self):
        # Load window and widgets
        self.builder = gtk.Builder()
        self.builder.add_from_file('/usr/share/device-driver-manager/ddm.glade')
        self.window = self.builder.get_object('ManagerWindow')
        self.lblText = self.builder.get_object('lblText')
        self.tvHardware = self.builder.get_object('tvHardware')
        self.btnInstall = self.builder.get_object('btnInstall')
        self.btnRemove = self.builder.get_object('btnRemove')
        self.btnClose = self.builder.get_object('btnClose')
        self.spinner = self.builder.get_object('spinner')
        self.statusbar = self.builder.get_object('statusbar')
        
        # Add events
        signals = {
            'on_tvHardware_cursor_changed' : self.cursorChanged,
            'on_btnInstall_clicked' : self.installHardware,
            'on_btnRemove_clicked' : self.removeHardware,
            'on_btnClose_clicked' : self.destroy,
            'on_eventbox_button_release_event' : self.about,
            'on_ManagerWindow_destroy' : self.destroy
        }
        self.builder.connect_signals(signals)
        
        self.window.show()
    
    # Fill the hardware tree view
    def fillHardware(self):
        hwFound = False
        contentList = []

        # Get a list of supported hardware and images
        self.hwList = DriverCheck(self.log).run()
        hwImgList = functions.getImgsFromDir(self.mediaDir)
        for item in self.hwList:
            hwFound = True
            hwImg = os.path.join(self.mediaDir, 'empty.png')
            install = True

            # Check if there is a hardware image available
            for img in hwImgList:
                if item[1] + '.png' in img:
                    self.log.write('Hardware image found: ' + img, 'ddm.fillHardware', 'info')
                    hwImg = img
                    break

            # Check the status of the driver
            statImg = os.path.join(self.mediaDir, item[2] + '.png')
            if item[1] in self.hwPreSelectList:
                install = True
            elif item[2] == functions.packageStatus[0] or item[2] == functions.packageStatus[2]:
                install = False
                
            # PAE check
            if item[1] == 'pae' and install:
                self.paeChecked = True
                
            # Add the row to the content list
            self.log.write('Add item: ' + item[0], 'ddm.fillHardware', 'info')
            self.log.write('Preselect: ' + str(install), 'ddm.fillHardware', 'debug')
            row = [install, statImg, hwImg, item[0], item[1], item[2]]
            contentList.append(row)
        
        # If nothing found: show message
        if not hwFound:
            columnTypesList = ['str']
            msg = 'No supported hardware detected'
            contentList.append(msg)
            self.log.write(msg, 'ddm.fillHardware', 'warning')
            functions.fillTreeview(self.tvHardware, contentList, columnTypesList)
            self.btnInstall.set_sensitive(False)
        else: 
            columnTypesList = ['bool', 'gtk.gdk.Pixbuf', 'gtk.gdk.Pixbuf', 'str', 'str', 'str']
            functions.fillTreeview(self.tvHardware, contentList, columnTypesList, [4,5])
    
    # Return the value of a given option
    def getValueForOption(self, searchList, option):
        val = ''
        for img in searchList:
            if img[0] == option:
                val = img[1]
                self.log.write('Value found in list: ' + val, 'ddm.getValueForOption', 'debug')
                break;
        return val
    
    # Get all the selected hardware drivers and pass this to the hardware driver install program (to be done)
    def handleHardware(self, actionString):
        hwSelected = False
        selHw = []
        selHwString = ''
        chkList = functions.getColumnValues(self.tvHardware, 0)
        parmList = functions.getColumnValues(self.tvHardware, 3)
        hwList = functions.getColumnValues(self.tvHardware, 4)
        statList = functions.getColumnValues(self.tvHardware, 5)
        for i in range(len(chkList)):
            if chkList[i]:
                self.log.write(actionString + ' hardware code: ' + hwList[i], 'ddm.handleHardware', 'info')
                selHw.append([hwList[i], statList[i]])
                hwSelected = True
        
        if hwSelected:
            # Install selected drivers
            self.toggleGuiElements(True)
            # Start saving in a separate thread
            self.log.write('Start driver ' + actionString + ' thread', 'ddm.handleHardware', 'info')
            if actionString == 'install':
                t = DriverInstall(selHw, self.log)
            else:
                t = DriverRemove(selHw, self.log)
            t.start()
            # Run spinner as long as the thread is alive
            self.log.write('Check every 5 seconds if thread is still active', 'ddm.installHardware', 'debug')
            glib.timeout_add(5, self.checkThread, actionString)
        else:
            msg = 'Select a driver to install.'
            MessageDialog('Driver install', msg , gtk.MESSAGE_INFO, self.window).show()
            
    def installHardware(self, widget):
        self.handleHardware('install')
    
    def removeHardware(self, widget):
        self.handleHardware('remove')

    def checkThread(self, actionString):
        #print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            self.spinner.start()
            return True        
        
        # Thread is done: stop spinner and make button sensitive again
        self.hwPreSelectList = []
        self.fillHardware()
        self.toggleGuiElements(False)
        # Show message that we're done
        if actionString == 'install':
            msg = 'Done installing drivers.'
        else:
            msg = 'Done removing drivers.'
        msg += '\n\nPlease, reboot your system.'
        MessageDialog('Driver ' + actionString, msg , gtk.MESSAGE_INFO, self.window).show()
        return False
    
    def toggleGuiElements(self, startSave):
        if startSave:
            self.btnInstall.set_sensitive(False)
            self.btnRemove.set_sensitive(False)
            self.btnClose.set_sensitive(False)
            self.tvHardware.set_sensitive(False)
            self.spinner.show()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.hide()
            self.btnInstall.set_sensitive(True)
            self.btnRemove.set_sensitive(True)
            self.btnClose.set_sensitive(True)
            self.tvHardware.set_sensitive(True)
        
    # Check if PAE is selected
    # PAE must be installed before any other drivers are installed
    def cursorChanged(self, treeview):
        hwCode = functions.getSelectedValue(self.tvHardware, 4)
        checked = functions.getSelectedValue(self.tvHardware, 0)
        
        if hwCode == 'pae':
            if checked:
                self.paeChecked = True
                if not self.hwPreSelectList:
                    msg = 'Install PAE before installing any other drivers.\n\nOther drivers are deselected (if any).'
                    MessageDialog('PAE install check', msg , gtk.MESSAGE_INFO, self.window).show()
                functions.treeviewToggleAll(self.tvHardware, 0, False, 4, 'pae')
            else:
                self.paeChecked = False
        else:
            if checked:
                if self.paeChecked:
                    if not self.hwPreSelectList:
                        msg = 'Install PAE before installing any other drivers\nor deselect PAE to install drivers for the current kernel'
                        MessageDialog('PAE install check', msg , gtk.MESSAGE_INFO, self.window).show()
                    functions.treeviewToggleAll(self.tvHardware, 0, False, 4, 'pae')
            
    def about(self, widget, event):
        self.about = self.builder.get_object('About')
        author = 'Author: ' + self.conf.getValue('About', 'author')
        email = 'E-mail: ' + self.conf.getValue('About', 'email')
        home = self.conf.getValue('About', 'home')
        comments = self.conf.getValue('About', 'comments')
        self.about.set_comments(author + '\n' + email + '\n\n' + comments)
        self.about.set_version(self.version)
        self.about.set_website(home)
        self.about.run()
        self.about.hide()
        
    def main(self, argv):
        # Handle arguments
        try:
            opts, args = getopt.getopt(argv, 'ic:dfl:', ['install', 'codes=', 'debug', 'force', 'log='])
        except getopt.GetoptError:
            print 'Arguments cannot be parsed: ' + str(argv)
            sys.exit(2)

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
        logFile = ''
        if self.debug:
            if self.logPath == '':
                self.logPath = 'ddm.log'
        self.log = Logger(self.logPath, 'debug', True, self.statusbar, self.window)
        functions.log = self.log
        
        # Set initial values
        self.text = self.conf.getValue('About', 'comments')
        self.lblText.set_text(self.text)
        
        # Show message that we're busy
        self.btnInstall.set_sensitive(False)
        self.btnRemove.set_sensitive(False)
        msg = 'Checking your hardware...'
        self.log.write(msg, 'ddm.main', 'info')
        functions.pushMessage(self.statusbar, msg)
        functions.repaintGui()

        # Fill hardware list
        self.fillHardware()
        self.btnInstall.set_sensitive(True)
        self.btnRemove.set_sensitive(True)
        
        # Show version number in status bar
        self.version = functions.getPackageVersion('device-driver-manager')
        functions.pushMessage(self.statusbar, self.version)

        # Start automatic install
        if self.install:
            self.log.write('Start automatic driver install', 'ddm.main', 'info')
            self.installHardware(None)
        
        # Show window and keep it on top of other windows
        self.window.set_keep_above(True)
        gtk.main()
    
    def destroy(self, widget, data=None):
        # Close the app
        gtk.main_quit()

        
if __name__ == '__main__':
    # Flush print when it's called
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # Create an instance of our GTK application
    app = DebianDriverManager()
    
    # Very dirty: replace the : back again with -
    # before passing the arguments
    args = sys.argv[1:]
    for i in range(len(args)):
        args[i] = string.replace(args[i], ':', '-')
    app.main(args)