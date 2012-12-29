#!/usr/bin/env python

try:
    import sys
    import os
    import gtk
    import gobject
except Exception, detail:
    print detail
    sys.exit(1)


# Treeview needs subclassing of gobject
# http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm

#def myCallback(self, obj, path, colNr, toggleValue, data=None):
#    print str(toggleValue)
#self.myTreeView = TreeViewHandler(self.myTreeView, self.myLogObject)
#self.myTreeView.connect('checkbox-toggled', self.myCallback)

class TreeViewHandler(gobject.GObject):

    __gsignals__ = {
        'checkbox-toggled': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_BOOLEAN,))
        }

    def __init__(self, loggerObject, treeView):
        gobject.GObject.__init__(self)
        self.log = loggerObject
        self.treeview = treeView

    # Clear treeview
    def clearTreeView(self):
        liststore = self.treeview.get_model()
        if liststore is not None:
            liststore.clear()
            self.treeview.set_model(liststore)

    # General function to fill a treeview
    # Set setCursorWeight to 400 if you don't want bold font
    def fillTreeview(self, contentList, columnTypesList, columnHideList=[-1], setCursor=0, setCursorWeight=400, firstItemIsColName=False, appendToExisting=False, appendToTop=False, fontSize=10000):
        # Check if this is a multi-dimensional array
        multiCols = self.isListOfLists(contentList)
        colNameList = []

        if len(contentList) > 0:
            liststore = self.treeview.get_model()
            if liststore is None:
                # Dirty but need to dynamically create a list store
                dynListStore = 'gtk.ListStore('
                for i in range(len(columnTypesList)):
                    dynListStore += str(columnTypesList[i]) + ', '
                dynListStore += 'int, int)'
                self.log.write('Create list store eval string: %s' % dynListStore, 'self.treeview.fillTreeview', 'debug')
                liststore = eval(dynListStore)
            else:
                if not appendToExisting:
                    # Existing list store: clear all rows and columns
                    self.log.write('Clear existing list store', 'self.treeview.fillTreeview', 'debug')
                    liststore.clear()
                    for col in self.treeview.get_columns():
                        self.treeview.remove_column(col)

            # Create list with column names
            if multiCols:
                for i in range(len(contentList[0])):
                    if firstItemIsColName:
                        self.log.write('First item is column name (multi-column list): %s' % contentList[0][i], 'self.treeview.fillTreeview', 'debug')
                        colNameList.append(contentList[0][i])
                    else:
                        colNameList.append('Column ' + str(i))
            else:
                if firstItemIsColName:
                    self.log.write('First item is column name (single-column list): %s' % contentList[0][i], 'self.treeview.fillTreeview', 'debug')
                    colNameList.append(contentList[0])
                else:
                    colNameList.append('Column 0')

            self.log.write('Create column names: %s' % str(colNameList), 'self.treeview.fillTreeview', 'debug')

            # Add data to the list store
            for i in range(len(contentList)):
                # Skip first row if that is a column name
                skip = False
                if firstItemIsColName and i == 0:
                    self.log.write('First item is column name: skip first item', 'self.treeview.fillTreeview', 'debug')
                    skip = True

                if not skip:
                    weight = 400
                    weightRow = setCursor
                    if firstItemIsColName:
                        weightRow += 1
                    if i == weightRow:
                        weight = setCursorWeight
                    if multiCols:
                        # Dynamically add data for multi-column list store
                        if appendToTop:
                            dynListStoreAppend = 'liststore.insert(0, ['
                        else:
                            dynListStoreAppend = 'liststore.append(['
                        for j in range(len(contentList[i])):
                            val = str(contentList[i][j])
                            if str(columnTypesList[j]) == 'str':
                                val = '"' + val + '"'
                            if str(columnTypesList[j]) == 'gtk.gdk.Pixbuf':
                                if os.path.isfile(val):
                                    val = 'gtk.gdk.pixbuf_new_from_file("%s")' % val
                                else:
                                    val = None
                            dynListStoreAppend += '%s, ' % val
                        dynListStoreAppend += '%s, %s])' % (str(weight), fontSize)

                        self.log.write('Add data to list store: %s' % dynListStoreAppend, 'self.treeview.fillTreeview', 'debug')
                        eval(dynListStoreAppend)
                    else:
                        if appendToTop:
                            self.log.write('Add data to top of list store: %s' % str(contentList[i]), 'self.treeview.fillTreeview', 'debug')
                            liststore.insert(0, [contentList[i], weight, fontSize])
                        else:
                            self.log.write('Add data to bottom of list store: %s' % str(contentList[i]), 'self.treeview.fillTreeview', 'debug')
                            liststore.append([contentList[i], weight, fontSize])

            # Check last visible column
            lastVisCol = -1
            for i in xrange(len(colNameList), 0, -1):
                if i in columnHideList:
                    lastVisCol = i - 1
                    self.log.write('Last visible column nr: %s' % str(lastVisCol), 'self.treeview.fillTreeview', 'debug')
                    break

            # Create columns
            for i in range(len(colNameList)):
                # Check if we have to hide this column
                skip = False
                for colNr in columnHideList:
                    if colNr == i:
                        self.log.write('Hide column nr: %s' % str(colNr), 'self.treeview.fillTreeview', 'debug')
                        skip = True

                if not skip:
                    # Create a column only if it does not exist
                    colFound = ''
                    cols = self.treeview.get_columns()
                    for col in cols:
                        if col.get_title() == colNameList[i]:
                            colFound = col.get_title()
                            break

                    if colFound == '':
                        # Build renderer and attributes to define the column
                        # Possible attributes for text: text, foreground, background, weight
                        attr = ', text=' + str(i) + ', weight=' + str(len(colNameList)) + ', size=' + str(len(colNameList) + 1)
                        renderer = 'gtk.CellRendererText()'  # an object that renders text into a gtk.TreeView cell
                        if str(columnTypesList[i]) == 'bool':
                            renderer = 'gtk.CellRendererToggle()'  # an object that renders a toggle button into a TreeView cell
                            attr = ', active=' + str(i)
                        if str(columnTypesList[i]) == 'gtk.gdk.Pixbuf':
                            renderer = 'gtk.CellRendererPixbuf()'  # an object that renders a pixbuf into a gtk.TreeView cell
                            attr = ', pixbuf=' + str(i)
                        dynCol = 'gtk.TreeViewColumn("' + str(colNameList[i]) + '", ' + renderer + attr + ')'

                        self.log.write('Create column: %s' % dynCol, 'self.treeview.fillTreeview', 'debug')
                        col = eval(dynCol)

                        # Get the renderer of the column and add type specific properties
                        rend = col.get_cell_renderers()[0]
                        #if str(columnTypesList[i]) == 'str':
                            # TODO: Right align text in column - add parameter to function
                            #rend.set_property('xalign', 1.0)
                        if str(columnTypesList[i]) == 'bool':
                            # If checkbox column, add toggle function
                            self.log.write('Check box found: add toggle function', 'self.treeview.fillTreeview', 'debug')
                            rend.connect('toggled', self.tvchk_on_toggle, liststore, i)

                        # Let the last colum fill the treeview
                        if i == lastVisCol:
                            self.log.write('Last column fills treeview: %s' % str(lastVisCol), 'self.treeview.fillTreeview', 'debug')
                            col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

                        # Finally add the column
                        self.treeview.append_column(col)
                        self.log.write('Column added: %s' % col.get_title(), 'self.treeview.fillTreeview', 'debug')
                    else:
                        self.log.write('Column already exists: %s' % colFound, 'self.treeview.fillTreeview', 'debug')

            # Add liststore, set cursor and set the headers
            self.treeview.set_model(liststore)
            if setCursor >= 0:
                self.treeview.set_cursor(setCursor)
            self.treeview.set_headers_visible(firstItemIsColName)
            self.log.write('Add Liststore to Treeview', 'self.treeview.fillTreeview', 'debug')

            # Scroll to selected cursor
            selection = self.treeview.get_selection()
            tm, treeIter = selection.get_selected()
            if treeIter:
                path = tm.get_path(treeIter)
                self.treeview.scroll_to_cell(path)
                self.log.write('Scrolled to selected row: %s' % str(setCursor), 'self.treeview.fillTreeview', 'debug')

    def tvchk_on_toggle(self, cell, path, liststore, colNr, *ignore):
        if path is not None:
            itr = liststore.get_iter(path)
            toggled = liststore[itr][colNr]
            liststore[itr][colNr] = not toggled
            # Raise the custom trigger
            # parameters: path, column number, toggle value
            self.emit('checkbox-toggled', path, colNr, not toggled)

    # Get the selected value in a treeview
    def getSelectedValue(self, colNr=0):
        # Assume single row selection
        (model, pathlist) = self.treeview.get_selection().get_selected_rows()
        return model.get_value(model.get_iter(pathlist[0]), colNr)

    # Get the value for a specific path (= row number)
    def getValue(self, path, colNr=0):
        model = self.treeview.get_model()
        return model.get_value(model.get_iter(path), colNr)

    # Return all the values in a given column
    def getColumnValues(self, colNr=0):
        cv = []
        model = self.treeview.get_model()
        itr = model.get_iter_first()
        while itr is not None:
            cv.append(model.get_value(itr, colNr))
            itr = model.iter_next(itr)
        return cv

    # Return the number of rows counted from iter
    # If iter is None, all rows are counted
    def getRowCount(self, startIter=None):
        model = self.treeview.get_model()
        return model.iter_n_children(startIter)

    # Toggle check box in row
    def treeviewToggleRows(self, toggleColNrList, pathList=None):
        if pathList is None:
            (model, pathList) = self.treeview.get_selection().get_selected_rows()
        else:
            model = self.treeview.get_model()
        # Toggle the check boxes in the given column in the selected rows (=pathList)
        for path in pathList:
            for colNr in toggleColNrList:
                it = model.get_iter(path)
                model[it][colNr] = not model[it][colNr]

    # Deselect all drivers, except PAE
    def treeviewToggleAll(self, toggleColNrList, toggleValue=False, excludeColNr=-1, excludeValue=''):
        model = self.treeview.get_model()
        itr = model.get_iter_first()
        while itr is not None:
            for colNr in toggleColNrList:
                if excludeColNr >= 0:
                    exclVal = model.get_value(itr, excludeColNr)
                    if exclVal != excludeValue:
                        model[itr][colNr] = toggleValue
                else:
                    model[itr][colNr] = toggleValue
                itr = model.iter_next(itr)

    def isListOfLists(self, lst):
        return len(lst) == len([x for x in lst if isinstance(x, list)])

# Register the class
gobject.type_register(TreeViewHandler)


# TODO - implement clickable image in TreeViewHandler
# http://www.daa.com.au/pipermail/pygtk/2010-March/018355.html
class CellRendererPixbufXt(gtk.CellRendererPixbuf):
    """docstring for CellRendererPixbufXt"""
    __gproperties__ = {'active-state':
                        (gobject.TYPE_STRING, 'pixmap/active widget state',
                        'stock-icon name representing active widget state',
                        None, gobject.PARAM_READWRITE)}
    __gsignals__ = {'clicked':
                        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()), }
    states = [None, gtk.STOCK_APPLY, gtk.STOCK_CANCEL]

    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)

    def do_get_property(self, property):
        """docstring for do_get_property"""
        if property.name == 'active-state':
            return self.active_state
        else:
            raise AttributeError('unknown property %s' % property.name)

    def do_set_property(self, property, value):
        if property.name == 'active-state':
            self.active_state = value
        else:
            raise AttributeError('unknown property %s' % property.name)
