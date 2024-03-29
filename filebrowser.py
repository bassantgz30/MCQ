# -*- coding: utf-8 -*-
"""
Created on Mon Sep 05 10:03:47 2016

@author: Bassant
"""

__all__ = ('FileBrowser', )
__version__ = '1.1-dev'

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.treeview import TreeViewLabel, TreeView
from kivy.uix.filechooser import FileChooserIconView as IconView

from kivy.properties import (ObjectProperty, StringProperty, OptionProperty,
                             ListProperty, BooleanProperty)
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivy.compat import PY2
import string
from os.path import sep, dirname, expanduser, isdir, join
from os import walk
from sys import getfilesystemencoding
from functools import partial

if platform == 'win':
    from ctypes import windll, create_unicode_buffer


def get_home_directory():
    if platform == 'win':
        user_path = expanduser('~')

        if not isdir(join(user_path, 'Desktop')):
            user_path = dirname(user_path)

    else:
        user_path = expanduser('~')

    if PY2:
        user_path = user_path.decode(getfilesystemencoding())

    return user_path


def get_drives():
    drives = []
    if platform == 'win':
        bitmask = windll.kernel32.GetLogicalDrives()
        GetVolumeInformationW = windll.kernel32.GetVolumeInformationW
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                name = create_unicode_buffer(64)
                # get name of the drive
                drive = letter + u':'
                res = GetVolumeInformationW(drive + sep, name, 64, None,
                                            None, None, None, 0)
                drives.append((drive, name.value))
            bitmask >>= 1
    elif platform == 'linux':
        drives.append((sep, sep))
        drives.append((expanduser(u'~'), '~/'))
        places = (sep + u'mnt', sep + u'media')
        for place in places:
            if isdir(place):
                for directory in next(walk(place))[1]:
                    drives.append((place + sep + directory, directory))
    elif platform == 'macosx' or platform == 'ios':
        drives.append((expanduser(u'~'), '~/'))
        vol = sep + u'Volume'
        if isdir(vol):
            for drive in next(walk(vol))[1]:
                drives.append((vol + sep + drive, drive))
    return drives

class FileBrowserIconView(IconView):
    pass

Builder.load_string('''
#:kivy 1.2.0
#:import metrics kivy.metrics
#:import abspath os.path.abspath
<TreeLabel>:
    on_touch_down:
        self.parent.browser.current_tab.content.path = self.path if\
        self.collide_point(*args[1].pos) and self.path else\
        self.parent.browser.current_tab.content.path
    on_is_open: self.is_open and self.parent.trigger_populate(self)
<FileBrowser>:
    id: fl
    orientation: 'vertical'
    spacing: 5
    padding: [6, 6, 6, 6]
    on_favorites: link_tree.reload_favs(self.favorites)
    BoxLayout:
        orientation: 'horizontal'
        spacing: 5
        Splitter:
            sizable_from: 'right'
            min_size: '153sp'
            size_hint: (.3, 1)
            id: splitter
            ScrollView:
                LinkTree:
                    id: link_tree
                    browser: tabbed_browser
                    size_hint_y: None
                    height: self.minimum_height
                    on_parent: self.fill_tree(root.favorites)
                    root_options: {'text': 'Locations', 'no_selection':True}
        BoxLayout:
            size_hint_x: 0.8
            orientation: 'vertical'
            Label:
                size_hint_y: None
                height: '22dp'
                text_size: self.size
                padding_x: '10dp'
                text: abspath(root.path)
                valign: 'middle'
            TabbedPanel:
                id: tabbed_browser
                do_default_tab: False
               
                TabbedPanelItem:
                    text: 'Icon View'
                    FileBrowserIconView:
                        id: icon_view
                        path: root.path
                        filters: root.filters
                        filter_dirs: root.filter_dirs
                        show_hidden: root.show_hidden
                        #multiselect: root.multiselect
                        dirselect: root.dirselect
                        rootpath: root.rootpath
                        on_submit: root.dispatch('on_submit')
    
        
                
        
       
''')


class TreeLabel(TreeViewLabel):
    path = StringProperty('')
    '''Full path to the location this node points to.
    :class:`~kivy.properties.StringProperty`, defaults to ''
    '''


class LinkTree(TreeView):
    # link to the favorites section of link bar
    _favs = ObjectProperty(None)
    _computer_node = None

    def fill_tree(self, fav_list):
        user_path = get_home_directory()
        self._favs = self.add_node(TreeLabel(text='Favorites', is_open=True,
                                             no_selection=True))
        self.reload_favs(fav_list)

        libs = self.add_node(TreeLabel(text='Libraries', is_open=True,
                                       no_selection=True))
        places = ('Documents', 'Music', 'Pictures', 'Videos')
        for place in places:
            if isdir(join(user_path, place)):
                self.add_node(TreeLabel(text=place, path=join(user_path,
                                        place)), libs)
        self._computer_node = self.add_node(TreeLabel(text='Computer',\
        is_open=True, no_selection=True))
        self._computer_node.bind(on_touch_down=self._drives_touch)
        self.reload_drives()

    def _drives_touch(self, obj, touch):
        if obj.collide_point(*touch.pos):
            self.reload_drives()

    def reload_drives(self):
        nodes = [(node, node.text + node.path) for node in\
                 self._computer_node.nodes if isinstance(node, TreeLabel)]
        sigs = [s[1] for s in nodes]
        nodes_new = []
        sig_new = []
        for path, name in get_drives():
            if platform == 'win':
                text = u'{}({})'.format((name + ' ') if name else '', path)
            else:
                text = name
            nodes_new.append((text, path))
            sig_new.append(text + path + sep)
        for node, sig in nodes:
            if sig not in sig_new:
                self.remove_node(node)
        for text, path in nodes_new:
            if text + path + sep not in sigs:
                self.add_node(TreeLabel(text=text, path=path + sep),
                              self._computer_node)

    def reload_favs(self, fav_list):
        user_path = get_home_directory()
        favs = self._favs
        remove = []
        for node in self.iterate_all_nodes(favs):
            if node != favs:
                remove.append(node)
        for node in remove:
            self.remove_node(node)
        places = ('Desktop', 'Downloads')
        for place in places:
            if isdir(join(user_path, place)):
                self.add_node(TreeLabel(text=place, path=join(user_path,
                                        place)), favs)
        for path, name in fav_list:
            if isdir(path):
                self.add_node(TreeLabel(text=name, path=path), favs)

    def trigger_populate(self, node):
        if not node.path or node.nodes:
            return
        parent = node.path
        _next = next(walk(parent))
        if _next:
            for path in _next[1]:
                self.add_node(TreeLabel(text=path, path=parent + sep + path),
                              node)


class FileBrowser(BoxLayout):
    '''FileBrowser class, see module documentation for more information.
    '''

    __events__ = ('on_canceled', 'on_success', 'on_submit')

    select_state = OptionProperty('normal', options=('normal', 'down'))
    '''State of the 'select' button, must be one of 'normal' or 'down'.
    The state is 'down' only when the button is currently touched/clicked,
    otherwise 'normal'. This button functions as the typical Ok/Select/Save
    button.
    :data:`select_state` is an :class:`~kivy.properties.OptionProperty`.
    '''
    cancel_state = OptionProperty('normal', options=('normal', 'down'))
    '''State of the 'cancel' button, must be one of 'normal' or 'down'.
    The state is 'down' only when the button is currently touched/clicked,
    otherwise 'normal'. This button functions as the typical cancel button.
    :data:`cancel_state` is an :class:`~kivy.properties.OptionProperty`.
    '''

 
    filename = StringProperty('')
    '''The current text in the filename field. Read only. When multiselect is
    True, the list of selected filenames is shortened. If shortened, filename
    will contain an ellipsis.
    :data:`filename` is an :class:`~kivy.properties.StringProperty`,
    defaults to ''.
    .. versionchanged:: 1.1
    '''

    selection = ListProperty([])
    '''Read-only :class:`~kivy.properties.ListProperty`.
    Contains the list of files that are currently selected in the current tab.
    See :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.selection`.
    .. versionchanged:: 1.1
    '''

    path = StringProperty(u'/')
    '''
    :class:`~kivy.properties.StringProperty`, defaults to the current working
    directory as a unicode string. It specifies the path on the filesystem that
    browser should refer to.
    See :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.path`.
    .. versionadded:: 1.1
    '''

    filters = ListProperty([])
    ''':class:`~kivy.properties.ListProperty`, defaults to [], equal to '\*'.
    Specifies the filters to be applied to the files in the directory.
    See :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.filters`.
    Filering keywords that the user types into the filter field as a comma
    separated list will be reflected here.
    .. versionadded:: 1.1
    '''

    filter_dirs = BooleanProperty(False)
    '''
    :class:`~kivy.properties.BooleanProperty`, defaults to False.
    Indicates whether filters should also apply to directories.
    See
    :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.filter_dirs`.
    .. versionadded:: 1.1
    '''

    show_hidden = BooleanProperty(False)
    '''
    :class:`~kivy.properties.BooleanProperty`, defaults to False.
    Determines whether hidden files and folders should be shown.
    See
    :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.show_hidden`.
    .. versionadded:: 1.1
    '''

    multiselect = BooleanProperty(True)
    '''
    :class:`~kivy.properties.BooleanProperty`, defaults to False.
    Determines whether the user is able to select multiple files or not.
    See
    :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.multiselect`.
    .. versionadded:: 1.1
    '''

    dirselect = BooleanProperty(True)
    '''
    :class:`~kivy.properties.BooleanProperty`, defaults to False.
    Determines whether directories are valid selections or not.
    See
    :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.dirselect`.
    .. versionadded:: 1.1
    '''

    rootpath = StringProperty(None, allownone=True)
    '''
    Root path to use instead of the system root path. If set, it will not show
    a ".." directory to go up to the root path. For example, if you set
    rootpath to /users/foo, the user will be unable to go to /users or to any
    other directory not starting with /users/foo.
    :class:`~kivy.properties.StringProperty`, defaults to None.
    See :kivy_fchooser:`kivy.uix.filechooser.FileChooserController.rootpath`.
    .. versionadded:: 1.1
    '''

    favorites = ListProperty([])
    '''A list of the paths added to the favorites link bar. Each element
    is a tuple where the first element is a string containing the full path
    to the location, while the second element is a string with the name of
    path to be displayed.
    :data:`favorites` is an :class:`~kivy.properties.ListProperty`,
    defaults to '[]'.
    '''

    def on_success(self):
        pass

    def on_canceled(self):
        pass

    def on_submit(self):
        pass

    def __init__(self, **kwargs):
        super(FileBrowser, self).__init__(**kwargs)
        Clock.schedule_once(self._post_init)

    def _post_init(self, *largs):
        self.ids.icon_view.bind(selection=partial(self._attr_callback, 'selection'),
                                path=partial(self._attr_callback, 'path'),
                                filters=partial(self._attr_callback, 'filters'),
                                filter_dirs=partial(self._attr_callback, 'filter_dirs'),
                                show_hidden=partial(self._attr_callback, 'show_hidden'),
                                multiselect=partial(self._attr_callback, 'multiselect'),
                                dirselect=partial(self._attr_callback, 'dirselect'),
                                rootpath=partial(self._attr_callback, 'rootpath'))
        

    def _shorten_filenames(self, filenames):
        if not len(filenames):
            return ''
        elif len(filenames) == 1:
            return filenames[0]
        elif len(filenames) == 2:
            return filenames[0] + ', ' + filenames[1]
        else:
            return filenames[0] + ', _..._, ' + filenames[-1]

    def _attr_callback(self, attr, obj, value):
        setattr(self, attr, getattr(obj, attr))

if __name__ == '__main__':
    import os
    from kivy.app import App

    