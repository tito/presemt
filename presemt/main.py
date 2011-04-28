'''
PreseMT - A presentation software
================================
'''

import kivy
kivy.require('1.0.6')

from sys import argv
from os.path import join, expanduser
from kivy.utils import QueryDict
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock

# even if it's not used in this current files
# behaviours are used into kv
import behaviours
import fbocapture


class PresemtApp(App):
    def __init__(self):
        super(PresemtApp, self).__init__()
        self.screens = {}
        self.config = QueryDict()

        # home directory + PresmtWs
        try:
            import android
            self.config.workspace_dir = join('/sdcard', '.presemt', 'workspace')
        except ImportError:
            self.config.workspace_dir = join(
                expanduser('~'), '.presemt', 'workspace')

    def show(self, name):
        '''Create and show a screen widget
        '''
        screens = self.screens
        modulename, clsname = name.split('.')
        if not name in screens:
            m = __import__('screens.%s' % modulename, fromlist=[modulename])
            cls = getattr(m, clsname)
            screens[name] = cls(app=self)
        screen = screens[name]
        self.root.clear_widgets()
        self.root.add_widget(screen)
        return screen

    def unload(self, name):
        if name in self.screens:
            del self.screens[name]

    def show_start(self):
        self.show('project.SelectorScreen')

    def create_empty_project(self):
        '''Create and start an empty project
        '''
        self.unload('presentation.MainScreen')
        return self.show('presentation.MainScreen')

    def play_project(self, filename):
        project = self.create_empty_project()
        project.filename = filename
        project.do_publish()

    def edit_project(self, filename):
        project = self.create_empty_project()
        project.filename = filename
        project.do_edit()

    def build(self):
        self.root = FloatLayout()
        self.show('loading.LoadingScreen')
        Clock.schedule_once(self._async_load, .5)

    def _async_load(self, dt):
        # ... do loading here ^^
        if len(argv) > 1:
            self.edit_project(argv[1])
        else:
            self.show('project.SelectorScreen')

if __name__ in ('__main__', '__android__'):
    PresemtApp().run()
