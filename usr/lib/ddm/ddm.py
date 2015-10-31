#! /usr/bin/env python3

# from gi.repository import Gtk, GdkPixbuf, GObject, Pango, Gdk, GLib
from gi.repository import Gtk, GObject, GLib
from os.path import join, abspath, dirname, basename, exists
from utils import ExecuteThreadedCommands, hasInternetConnection, \
                  getoutput, getPackageVersion, has_backports
import os
import re
from glob import glob
from dialogs import MessageDialog, WarningDialog, ErrorDialog, QuestionDialog
from treeview import TreeViewHandler
from queue import Queue
from logger import Logger

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('ddm')

# Need to initiate threads for Gtk
GObject.threads_init()


#class for the main window
class DDM(object):

    def __init__(self, test=False):
        # Testing
        self.test = test
        # Set to true for testing Optimus
        self.test_optimus = False

        # Load window and widgets
        self.scriptName = basename(__file__)
        self.scriptDir = abspath(dirname(__file__))
        self.mediaDir = join(self.scriptDir, '../../share/ddm')
        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(self.mediaDir, 'ddm.glade'))

        # Main window objects
        go = self.builder.get_object
        self.window = go("ddmWindow")
        self.tvDDM = go("tvDDM")
        self.btnSave = go("btnSave")
        self.btnHelp = go("btnHelp")
        self.btnQuit = go("btnQuit")
        self.pbDDM = go("pbDDM")
        self.chkBackports = go("chkBackports")

        self.window.set_title(_("Device Driver Manager"))
        self.btnSave.set_label(_("Install"))
        self.btnHelp.set_label(_("Help"))
        self.btnQuit.set_label(_("Quit"))
        self.chkBackports.set_label(_("Use Backports"))

        # Initiate variables
        self.queue = Queue(-1)
        self.threads = {}
        self.hardware = []
        self.loadedDrivers = []
        self.notSupported = []
        self.paeBooted = False
        self.htmlDir = join(self.mediaDir, "html")
        self.helpFile = join(self.get_language_dir(), "help.html")
        self.logFile = '/var/log/ddm.log'
        self.log = Logger(self.logFile, addLogTime=False, maxSizeKB=5120)
        self.tvDDMHandler = TreeViewHandler(self.tvDDM)
        self.tvDDMHandler.connect('checkbox-toggled', self.tv_checkbox_toggled)

        # Connect builder signals and show window
        self.builder.connect_signals(self)
        self.window.show_all()

        # Fill treeview
        self.fill_treeview_ddm()

        # Check backports
        if len(self.hardware) < 2 or not has_backports():
            self.chkBackports.hide()

        self.get_loaded_graphical_driver()
        self.get_loaded_wireless_driver()

    # ===============================================
    # Language specific functions
    # ===============================================

    def get_language_dir(self):
        # First test if full locale directory exists, e.g. html/pt_BR,
        # otherwise perhaps at least the language is there, e.g. html/pt
        lang = self.get_current_language()
        path = os.path.join(self.htmlDir, lang)
        if path != self.htmlDir:
            if not os.path.isdir(path):
                path = os.path.join(self.htmlDir, lang.split('_')[0].lower())
                if not os.path.isdir(path):
                    return os.path.join(self.htmlDir, 'en')
            return path
        # else, just return English slides
        return os.path.join(self.htmlDir, 'en')

    def get_current_language(self):
        return os.environ.get('LANG', 'US').split('.')[0]

    # ===============================================
    # Main window functions
    # ===============================================

    def on_btnSave_clicked(self, widget):
        # Save selected hardware
        arguments = []

        model = self.tvDDM.get_model()
        itr = model.get_iter_first()
        while itr is not None:
            action = 'no change'
            selected = model.get_value(itr, 0)
            device = model.get_value(itr, 2)
            manufacturerId = ''

            # Check currently selected state with initial state
            # This decides whether we should install or purge the drivers
            for hw in self.hardware:
                self.log.write("Device = {} in {}".format(device, hw[2]), 'on_btnSave_clicked')
                if device in hw[2]:
                    manufacturerId = hw[4]
                    if hw[0] and not selected:
                        action = 'purge'
                    elif not hw[0] and selected:
                        action = 'install'
                    break

            self.log.write("{}: {} ({})".format(action, device, manufacturerId), 'on_btnSave_clicked')

            # Install/purge selected driver
            option = ""
            if action == 'install':
                option = "-i"
            elif action == 'purge':
                option = "-p"

            if option:
                driver = ''
                # Run the manufacturer specific bash script
                if manufacturerId == '1002':
                    driver = 'ati'
                elif manufacturerId == '10de':
                    driver = 'nvidia '
                elif manufacturerId == '14e4':
                    driver = 'broadcom '
                elif 'pae' in manufacturerId:
                    driver = 'pae '
                if driver:
                    arguments.append("{} {}".format(option, driver))

            # Get the next in line
            itr = model.iter_next(itr)

        # Execute the command
        if arguments:
            if '-i' in arguments and not hasInternetConnection():
                title = _("No internet connection")
                msg = _("You need an internet connection to install the additional software.\n"
                        "Please, connect to the internet and try again.")
                WarningDialog(title, msg)
            else:
                # Warn for use of Backports
                if self.chkBackports.get_active():
                    answer = QuestionDialog(self.chkBackports.get_label(),
                            _("You have selected to install drivers from the backports repository whenever they are available.\n\n"
                              "Although you can run more up to date software using the backports repository,\n"
                              "you introduce a greater risk of breakage doing so.\n\n"
                              "Are you sure you want to continue?"))
                    if not answer:
                        self.chkBackports.set_active(False)
                        return True
                    arguments.append("-b")

                # Testing
                if self.test:
                    arguments.append("-t")

                command = "ddm {}".format(" ".join(arguments))
                self.log.write("Command to execute: {}".format(command), 'on_btnSave_clicked')
                self.exec_command(command)

    def on_btnQuit_clicked(self, widget):
        self.on_ddmWindow_destroy(widget)

    def on_btnHelp_clicked(self, widget):
        # Open the help file as the real user (not root)
        logname = getoutput('logname')[0]
        ff = '/opt/firefox/firefox'
        if exists(ff):
            os.system("su {} -c \"{} {}\" &".format(logname, ff, self.helpFile))
        else:
            # If Firefox was removed, this might work
            os.system("su {} -c \"xdg-open {}\" &".format(logname, self.helpFile))

    def get_supported_hardware(self):
        # Fill self.hardware
        self.hardware = []

        # First row are column names
        self.hardware.append([_("Install"), '', _("Device"), 'driver', 'manid', 'deviceid'])

        # Get hardware information
        self.get_ati()
        self.get_nvidia()
        self.get_broadcom()
        self.get_pae()

    # This method is fired by the TreeView.checkbox-toggled event
    def tv_checkbox_toggled(self, obj, path, colNr, toggleValue):
        path = int(path)
        model = self.tvDDM.get_model()
        itr = model.get_iter(path)
        description = model[itr][2].lower()

        if 'pae' in description and not toggleValue and self.paeBooted:
            title = _("Remove kernel")
            msg = _("You cannot remove a booted kernel.\nPlease, boot another kernel and try again.")
            self.log.write(msg, 'tv_checkbox_toggled')
            WarningDialog(title, msg)
            model[itr][0] = True

    def fill_treeview_ddm(self):
        # Fill a list with supported hardware
        self.get_supported_hardware()

        # columns: checkbox, image (logo), device, driver
        columnTypes = ['bool', 'GdkPixbuf.Pixbuf', 'str']

        # Keep some info from the user
        showHw = []
        for hw in self.hardware:
            showHw.append([hw[0], hw[1], hw[2]])

        # Fill treeview
        self.tvDDMHandler.fillTreeview(contentList=showHw, columnTypesList=columnTypes, firstItemIsColName=True, fontSize=12000)

        # Show message if nothing is found or hardware is not supported
        title = _("Hardware scan")
        if self.notSupported:
            if len(self.hardware) < 2:
                self.set_buttons_state(False)
            msg = _("There are no available drivers for your hardware:")
            msg = "{}\n\n{}".format(msg, '\n'.join(self.notSupported))
            self.log.write(msg, 'fill_treeview_ddm')
            WarningDialog(title, msg)
        elif len(self.hardware) < 2:
            self.set_buttons_state(False)
            msg = _("DDM did not find any supported hardware.")
            self.log.write(msg, 'fill_treeview_ddm')
            MessageDialog(title, msg)

    def exec_command(self, command):
        try:
            # Run the command in a separate thread
            self.set_buttons_state(False)
            name = 'cmd'
            t = ExecuteThreadedCommands([command], self.queue)
            self.threads[name] = t
            t.daemon = True
            t.start()
            self.queue.join()
            GLib.timeout_add(250, self.check_thread, name)

        except Exception as detail:
            ErrorDialog(self.btnSave.get_label(), detail)

    def set_buttons_state(self, enable):
        if not enable:
            # Disable buttons
            self.btnSave.set_sensitive(False)
        else:
            # Enable buttons and reset progress bar
            self.btnSave.set_sensitive(True)
            self.pbDDM.set_fraction(0)

    def check_thread(self, name):
        if self.threads[name].is_alive():
            self.pbDDM.pulse()
            if not self.queue.empty():
                ret = self.queue.get()
                self.log.write("Queue returns: {}".format(ret), 'check_thread')
                self.queue.task_done()
                self.show_message(ret)
            return True

        # Thread is done
        self.log.write(">> Thread is done", 'check_thread')
        if not self.queue.empty():
            ret = self.queue.get()
            self.queue.task_done()
            self.show_message(ret)
        del self.threads[name]

        self.set_buttons_state(True)

        return False

    # Close the gui
    def on_ddmWindow_destroy(self, widget):
        # Close the app
        Gtk.main_quit()

    # ===============================================
    # Hardware functions
    # ===============================================

    def get_ati(self):
        # Debian Wiki: https://wiki.debian.org/ATIProprietary
        # Supported devices 14.9 (Jessie): http://support.amd.com/en-us/kb-articles/Pages/AMDCatalyst14-9LINReleaseNotes.aspx

        manufacturerId = '1002'
        startSeries = 5000
        deviceArray = self.get_lspci_info(manufacturerId, 'VGA')

        if self.test:
            #deviceArray = [['Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series]', manufacturerId, '68e0']]
            #deviceArray = [['Advanced Micro Devices, Inc. [AMD/ATI] RV710 [Radeon HD 4350/4550]', manufacturerId, '68e0']]
            #deviceArray = [['Advanced Micro Devices [AMD/ATI] RS880 [Radeon HD 4290]', manufacturerId, '68e0']]
            #deviceArray = [['Advanced Micro Devices, Inc. [AMD/ATI] Tonga PRO [Radeon R9 285]', manufacturerId, '6939']]
            deviceArray = [['Advanced Micro Devices, Inc. [AMD/ATI] Bonaire [FirePro W5100]', manufacturerId, '6649']]

        if deviceArray:
            self.log.write("Device(s): {}".format(deviceArray), 'get_ati')
            # Check if fglrx is loaded
            # If it is: checkbox is selected
            loadedDrv = self.get_loaded_graphical_driver()
            self.log.write("Loaded graphical driver: {}".format(loadedDrv), 'get_ati')

            # Get the manufacturer's logo
            logo = join(self.mediaDir, 'images/ati.png')

            # Fill the hardware array
            for device in deviceArray:
                self.log.write("ATI device found: {}".format(device[0]), 'get_ati')
                # Check for supported cards
                matchObj = re.search('radeon\s+[0-9a-z ]+|fire[a-z]+\s+[0-9a-z -]+', device[0], flags=re.IGNORECASE)
                if matchObj:
                    if " hd " in matchObj.group(0).lower():
                        # Check if ATI series is above 5000
                        matchObjSeries = re.search('[0-9]{4}', matchObj.group(0))
                        if matchObjSeries:
                            series = int(matchObjSeries.group(0))
                            # Don't show older ATI Radeon HD cards
                            if series < startSeries:
                                break
                    elif 'fire' in matchObj.group(0).lower():
                        title = _("ATI FirePro/Gl card found")
                        msg = _("Installing the proprietary driver for an ATI FirePro/Gl card may render your system unbootable.\n\n"
                                "Proceed at your own risk.")
                        self.log.write(msg, 'get_ati')
                        WarningDialog(title, msg)

                    self.log.write("ATI series: {}".format(matchObj.group(0)), 'get_ati')

                    # Check if the available driver is already loaded
                    selected = False
                    driver = 'fglrx'
                    if loadedDrv == driver:
                        selected = True

                    # Fill self.hardware
                    #shortDevice = self.shorten_long_string(device[0], 100)
                    self.hardware.append([selected, logo, device[0], driver, device[1], device[2]])
                else:
                    self.notSupported.append(device[0])

    def get_nvidia(self):
        manufacturerId = '10de'
        deviceArray = self.get_lspci_info(manufacturerId, 'VGA')

        if self.test:
            deviceArray = [['NVIDIA Corporation GT218 [GeForce G210M]', manufacturerId, '0a74']]
            if self.test_optimus:
                deviceArray = [['Intel Corporation Haswell-ULT Integrated Graphics Controller', '8086', '0a16'], \
                                ['NVIDIA Corporation GK107M [GeForce GT 750M]', manufacturerId, '0fe4']]

        if deviceArray:
            optimus = False
            devices = []

            self.log.write("Device(s): {}".format(deviceArray), 'get_nvidia')

            # Check if nvidia is loaded
            # If it is: checkbox is selected
            loadedDrv = self.get_loaded_graphical_driver()
            self.log.write("Loaded graphical driver: {}".format(loadedDrv), 'get_nvidia')

            # Get the manufacturer's logo
            logo = join(self.mediaDir, 'images/nvidia.png')

            # Fill the hardware array
            for device in deviceArray:
                if device[1] == '8086':
                    optimus = True
                else:
                    devices.append(device)

            for device in devices:
                self.log.write("Nvidia device found: {}".format(device[0]), 'get_nvidia')
                optimusString = ""
                if optimus:
                    optimusString = "(Optimus) "

                # Check if the available driver is already loaded
                selected = False
                if optimus:
                    if loadedDrv == 'nvidia' or loadedDrv == 'intel':
                        bbversion = getPackageVersion("bumblebee-nvidia")
                        self.log.write("bumblebee-nvidia version: {}".format(bbversion), 'get_nvidia')
                        if bbversion != '':
                            selected = True
                elif loadedDrv == 'nvidia':
                    selected = True

                driver = ""
                if optimus:
                    driver = "bumblebee-nvidia"
                else:
                    if self.test:
                        driver = 'nvidia-driver'
                    else:
                        nvidiaDetect = getoutput("nvidia-detect | grep nvidia- | tr -d ' '")
                        if nvidiaDetect:
                            driver = nvidiaDetect[0]

                self.log.write("Nvidia driver to use: {}".format(driver), 'get_nvidia')

                # Fill self.hardware
                if driver != "":
                    #shortDevice = "{0}{1}".format(optimusString, self.shorten_long_string(device[0], 100))
                    self.hardware.append([selected, logo, "{0}{1}".format(optimusString, device[0]), driver, device[1], device[2]])

    def get_broadcom_ids(self, driver_name):
        driver_name = driver_name.upper()
        ids = getoutput("cat /usr/bin/ddm | grep '{}=' | cut -d'=' -f 2".format(driver_name))
        if len(ids) > 0:
            return ids[0].split('|')
        return []

    def get_broadcom(self):
        ## Hardware list (device ids)
        ## http://linuxwireless.org/en/users/Drivers/b43
        deviceIds = {}
        deviceIds['b43'] = self.get_broadcom_ids('b43')
        deviceIds['b43legacy'] = self.get_broadcom_ids('b43legacy')
        deviceIds['wldebian'] = self.get_broadcom_ids('wldebian')
        deviceIds['brcmdebian'] = self.get_broadcom_ids('brcmdebian')
        deviceIds['unknown'] = self.get_broadcom_ids('unknown')

        self.log.write("Broadcom deviceIds = {}".format(deviceIds))

        manufacturerId = '14e4'

        deviceArray = self.get_lspci_info(manufacturerId)

        if self.test:
            deviceArray = [['Broadcom Corporation BCM43142 802.11a/b/g', manufacturerId, '4365']]

        if deviceArray:
            self.log.write("Device(s): {}".format(deviceArray), 'get_broadcom')
            # Check if broadcom is loaded
            # If it is: checkbox is selected
            loadedDrv = self.get_loaded_wireless_driver()
            self.log.write("Loaded wireless driver: {}".format(loadedDrv), 'get_broadcom')

            # Get the manufacturer's logo
            logo = join(self.mediaDir, 'images/broadcom.png')

            # Fill the hardware array
            for device in deviceArray:
                self.log.write("Broadcom device found: {}".format(device[0]), 'get_broadcom')
                driver = ''
                for key, did in list(deviceIds.items()):
                    #print(("{}:{} in {}:{}".format(device[0], device[2], key, did)))
                    if device[2] in did:
                        driver = key
                        break

                if driver != '':
                    if driver == 'unknown':
                        self.notSupported.append(device[0])
                        self.log.write("Broadcom device not supported: {}".format(device[0]), 'get_broadcom')
                    else:
                        self.log.write("Broadcom driver to use: {}".format(driver), 'get_broadcom')
                        # Check if the available driver is already loaded
                        selected = False
                        if loadedDrv == driver:
                            selected = True

                        # Fill self.hardware
                        #shortDevice = self.shorten_long_string(device[0], 100)
                        self.hardware.append([selected, logo, device[0], driver, device[1], device[2]])

    def get_pae(self):
        machine = getoutput('uname -m')[0]
        release = getoutput('uname -r')[0]

        if self.test:
            machine = 'i686'
            release = '3.16.0-4-586'

        self.log.write("PAE check: machine={} / release={}".format(machine, release), 'get_pae')

        if machine == 'i686':
            # Check if PAE is installed and running
            selected = False
            if 'pae' in release:
                self.paeBooted = True
                selected = True
            else:
                if getPackageVersion('linux-image-686-pae') != '':
                    selected = True

            # Get the logo
            logo = join(self.mediaDir, 'images/pae.png')

            # Fill self.hardware
            paeDescription = _("PAE capable system")
            self.hardware.append([selected, logo, paeDescription, '', 'pae', ''])

    def get_lspci_info(self, manufacturerId, filterString=''):
        deviceArray = []
        output = []

        # Check for Optimus
        if manufacturerId == '10de':
            output = getoutput("lspci -vnn | grep '\[030[02]\]'")

            if self.test_optimus:
                output = ['00:02.0 VGA compatible controller [0300]: Intel Corporation Haswell-ULT Integrated Graphics Controller [8086:0a16] (rev 09) (prog-if 00 [VGA controller])', \
                          '01:00.0 3D controller [0302]: NVIDIA Corporation GK107M [GeForce GT 750M] [10de:0fe4] (rev a1)']

        # Optimus will return 2 devices
        # If there are less than 2 devices, do regular check
        if len(output) < 2:
            if filterString != '':
                filterString = " | grep {}".format(filterString)
            output = getoutput("lspci -nn -d {}:{}".format(manufacturerId, filterString))

        if output:
            self.log.write("lspci output = {}".format(output), 'get_lspci_info')

        for line in output:
            matchObj = re.search(':\W(.*)\W\[(.+):(.+)\]', line)
            if matchObj:
                deviceArray.append([matchObj.group(1), matchObj.group(2), matchObj.group(3)])
        return deviceArray

    def shorten_long_string(self, longString, charLen, breakOnWord=True):
        tmpArr = []
        if breakOnWord:
            stringArr = longString.split(' ')
            nrChrs = 0
            for s in stringArr:
                nrChrs += len(s) + 1
                if nrChrs < charLen:
                    tmpArr.append(s)
                else:
                    break
        else:
            if len(longString) > charLen:
                tmpArr.append("{}...".format(longString[0:charLen]))
            else:
                tmpArr.append(longString)
        return ' '.join(tmpArr)

    # Return graphics module used by X.org
    # TODO: is lsmod an alternative?
    def get_loaded_graphical_driver(self):
        # sort on the most recent X.org log
        module = ''
        log = ''
        logDir = '/var/log/'
        logPath = None
        logs = glob(os.path.join(logDir, 'Xorg.*.log*'))
        logs.sort()

        for logPath in logs:
            # Search for "depth" in each line and check the used module
            # Sometimes these logs are saved as binary: open as read-only binary
            # When opening as ascii, read() will throw error: "UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80"
            with open(logPath, 'rb') as f:
                # replace utf-8 binary read errors (with ?)
                log = f.read().decode(encoding='utf-8', errors='replace')
                #print((log))

            matchObj = re.search('([a-zA-Z]*)\(\d+\):\s+depth.*framebuffer', log, flags=re.IGNORECASE)
            if matchObj:
                module = matchObj.group(1).lower()
                self.log.write("Log module={}".format(module))
                break

        return module

    # Return used wireless driver
    def get_loaded_wireless_driver(self):
        driver = ''
        logDir = '/var/log/'
        for logPath in glob(os.path.join(logDir, 'syslog*')):
            if driver == '' and not 'gz' in logPath:
                # Open the log file
                lines = []
                with open(logPath) as f:
                    lines = list(f.read().splitlines())

                for line in reversed(lines):
                    # First check for Network Manager entry
                    # Search for wlan0 in each line and get the listed driver
                    matchObj = re.search('\(wlan\d\):.*driver:\s*\'([a-zA-Z0-9\-]*)', line, flags=re.IGNORECASE)
                    if matchObj:
                        driver = matchObj.group(1)
                        self.log.write("Network Manager driver={}".format(driver))
                        break
                    else:
                        # Wicd
                        # Search for ieee in each line and get the listed driver
                        matchObj = re.search('ieee.*implement', line, flags=re.IGNORECASE)
                        if matchObj:
                            driver = matchObj.group(0)
                            self.log.write("Wicd driver={}".format(driver))
                            break

        return driver

    def show_message(self, cmdOutput):
        try:
            self.log.write("Command output: {}".format(cmdOutput), 'show_message')
            ret = int(cmdOutput)
            if ret > 1 and ret != 255:
                if ret == 1:
                    ErrorDialog(self.btnSave.get_label(), _("Run as root."))
                elif ret == 2:
                    ErrorDialog(self.btnSave.get_label(), _("Wrong arguments passed to ddm."))
                elif ret == 3:
                    ErrorDialog(self.btnSave.get_label(), _("There are no driver available."))
                elif ret == 4:
                    ErrorDialog(self.btnSave.get_label(), _("The driver cannot be found in repository."))
                elif ret == 5:
                    ErrorDialog(self.btnSave.get_label(), _("Download error.\nCheck your internet connection."))
                elif ret == 6:
                    ErrorDialog(self.btnSave.get_label(), _("DDM cannot purge the driver."))
                elif ret == 7:
                    ErrorDialog(self.btnSave.get_label(), _("This card is not supported."))
                else:
                    msg = _("There was an error during the installation.\n"
                    "Please, run 'sudo apt-get -f install' in a terminal.\n"
                    "Visit our forum for support: http://forums.solydxk.com")
                    ErrorDialog(self.btnSave.get_label(), msg)
            else:
                msg = _("The software has been successfully installed.")
                msg_restart = _("You will need to restart your system.")
                MessageDialog(self.btnSave.get_label(), "{}\n\n{}".format(msg, msg_restart))
        except:
            ErrorDialog(self.btnSave.get_label(), cmdOutput)
