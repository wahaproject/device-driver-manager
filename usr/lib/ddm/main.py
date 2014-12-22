#!/usr/bin/python -OO
#-*- coding: utf-8 -*-

import sys
sys.path.insert(1, '/usr/lib/ddm')
from gi.repository import Gtk
from ddm import DDM
import os
import getopt

# Handle arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], 'f', ['force'])
except getopt.GetoptError:
    sys.exit(2)

force = False
for opt, arg in opts:
    print((">> opt = {} / arg = {}".format(opt, arg)))
    if opt in ('-f', '--force'):
        force = True


# Set variables
scriptDir = os.path.dirname(os.path.realpath(__file__))
title = _("Device Driver Manager")
msg = _("Device Driver Manager cannot be started in a live environment\n"
        "You can use the --force argument to start DDM in a live environment")


def isRunningLive():
    if force:
        return False
    liveDirs = ['/live', '/lib/live', '/rofs']
    for ld in liveDirs:
        if os.path.exists(ld):
            return True
    return False


def showMsg(title, message, GtkMessageType=Gtk.MessageType.INFO):
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, GtkMessageType, Gtk.ButtonsType.OK, message)
    dialog.set_markup("<b>{}</b>".format(title))
    dialog.format_secondary_markup(message)
    dialog.set_icon_name("ddm")
    dialog.run()
    dialog.destroy()


# Do not run in live environment
if isRunningLive():
    showMsg(title, msg)
    sys.exit()


def uncaught_excepthook(*args):
    sys.__excepthook__(*args)
    if __debug__:
        from pprint import pprint
        from types import BuiltinFunctionType, ClassType, ModuleType, TypeType
        tb = sys.last_traceback
        while tb.tb_next: tb = tb.tb_next
        print('\nDumping locals() ...')
        pprint({k:v for k,v in tb.tb_frame.f_locals.items()
                    if not k.startswith('_') and
                       not isinstance(v, (BuiltinFunctionType,
                                          ClassType, ModuleType, TypeType))})
        if sys.stdin.isatty() and (sys.stdout.isatty() or sys.stderr.isatty()):
            try:
                import ipdb as pdb  # try to import the IPython debugger
            except ImportError:
                import pdb as pdb
            print('\nStarting interactive debug prompt ...')
            pdb.pm()
    else:
        import traceback
        title = _('Unexpected error')
        msg = _('Device Driver Manager has failed with the following unexpected error.\nPlease submit a bug report!')
        msg = "<b>{}</b>\n\n<tt>{}</tt>".format(msg, '\n'.join(traceback.format_exception(*args)))
        showMsg(title, msg)
    sys.exit(1)

sys.excepthook = uncaught_excepthook

# main entry
if __name__ == "__main__":
    # Create an instance of our GTK application
    try:
        DDM()
        Gtk.main()
    except KeyboardInterrupt:
        pass
