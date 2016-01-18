#! /usr/bin/env python3 -OO

# Make sure the right Gtk version is loaded
import gi
gi.require_version('Gtk', '3.0')

import sys
sys.path.insert(1, '/usr/lib/ddm')
from dialogs import MessageDialog, ErrorDialog, WarningDialog
from gi.repository import Gtk, GObject
from ddm import DDM
import os
import argparse


# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('ddm')


# Handle arguments
parser = argparse.ArgumentParser(description="DDM")
parser.add_argument('-t', action="store_true", help='Testing only: install drivers for pre-defined hardware')
parser.add_argument('-f', action="store_true", help='Force DDM to start even in a live environment')
args, extra = parser.parse_known_args()
test = args.t
force = args.f


# Warn for the use of proprietary drivers
title = _("Device Driver Manager")
msg = _("Device Driver Manager helps to install proprietary drivers for your hardware.\n"
        "Only install proprietary drivers if you are sure you really need them.\n"
        "Usually open drivers are enough.")
WarningDialog(title, msg, None, None, True, 'ddm')


# Set variables
scriptDir = os.path.dirname(os.path.realpath(__file__))


def isRunningLive():
    if force:
        return False
    liveDirs = ['/live', '/lib/live/mount', '/rofs']
    for ld in liveDirs:
        if os.path.exists(ld):
            return True
    return False


# Do not run in live environment
if isRunningLive():
    msg = _("Device Driver Manager cannot be started in a live environment\n"
            "You can use the --force argument to start DDM in a live environment")
    MessageDialog(title, msg, None, None, True, 'ddm')
    sys.exit()


def uncaught_excepthook(*args):
    sys.__excepthook__(*args)
    if __debug__:
        from pprint import pprint
        from types import BuiltinFunctionType, ClassType, ModuleType, TypeType
        tb = sys.last_traceback
        while tb.tb_next: tb = tb.tb_next
        print(('\nDumping locals() ...'))
        pprint({k:v for k,v in tb.tb_frame.f_locals.items()
                    if not k.startswith('_') and
                       not isinstance(v, (BuiltinFunctionType,
                                          ClassType, ModuleType, TypeType))})
        if sys.stdin.isatty() and (sys.stdout.isatty() or sys.stderr.isatty()):
            try:
                import ipdb as pdb  # try to import the IPython debugger
            except ImportError:
                import pdb as pdb
            print(('\nStarting interactive debug prompt ...'))
            pdb.pm()
    else:
        import traceback
        details = '\n'.join(traceback.format_exception(*args)).replace('<', '').replace('>', '')
        title = _('Unexpected error')
        msg = _('DDM has failed with the following unexpected error. Please submit a bug report!')
        ErrorDialog(title, "<b>%s</b>" % msg, "<tt>%s</tt>" % details, None, True, 'ddm')

    sys.exit(1)

sys.excepthook = uncaught_excepthook

# main entry
if __name__ == "__main__":
    # Create an instance of our GTK application
    try:
        # Calling GObject.threads_init() is not needed for PyGObject 3.10.2+
        # Check with print (sys.version)
        # Debian Jessie: 3.4.2
        GObject.threads_init()

        DDM(test)
        Gtk.main()
    except KeyboardInterrupt:
        pass
