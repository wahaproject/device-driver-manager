#!/usr/bin/env python

try:
    import gtk
    import gobject
except Exception, detail:
    print detail

# Show message dialog
# Usage:
# MessageDialog(_("My Title"), "Your (error) message here", gtk.MESSAGE_ERROR).show()
# Message types:
# gtk.MESSAGE_INFO
# gtk.MESSAGE_WARNING
# gtk.MESSAGE_ERROR
# MessageDialog can be called from a working thread     
class MessageDialog(gtk.MessageDialog):
    def __init__(self, title, message, style, parent=None):
        gtk.MessageDialog.__init__(self, parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, style, gtk.BUTTONS_OK, message)
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title(title)
        if parent != None:
            self.set_icon(parent.get_icon())
        self.connect('response', self._handle_clicked)
 
    def _handle_clicked(self, *args):
        self.destroy()
 
    def show(self):
        gobject.timeout_add(0, self._do_show_dialog)
 
    def _do_show_dialog(self):
        self.show_all()
        return False
 

# Create question dialog
# Usage:
# dialog = QuestionDialog(_("My Title"), _("Put your question here?"))
#    if (dialog.show()):
# QuestionDialog can NOT be called from a working thread, only from main (UI) thread
class QuestionDialog(object):
    def __init__(self, title, message, parent=None):
        self.title = title
        self.message = message
        if parent != None:
            self.set_icon(parent.get_icon())

    ''' Show me on screen '''
    def show(self):
        dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, self.message)
        dialog.set_title(self.title)
        dialog.set_position(gtk.WIN_POS_CENTER)
        dialog.set_icon(self.icon)
        answer = dialog.run()
        if answer==gtk.RESPONSE_YES:
            return_value = True
        else:
            return_value = False
        dialog.destroy()
        return return_value