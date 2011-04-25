'''
PreseMT - A presentation software
================================
'''

import kivy
kivy.require('1.0.5')

from sys import argv
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

# even if it's not used in this current files
# behaviours are used into kv
import behaviours


class PresemtApp(App):
    def __init__(self):
        super(PresemtApp, self).__init__()
        self.screens = {}

    def create_empty_project(self):
        '''Create and start an empty project
        '''
        self.show('presentation.MainScreen')

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

    def show_start(self):
        self.show('project.SelectorScreen')

    def build(self):
        self.root = FloatLayout()
        self.show('loading.LoadingScreen')
        # ... do loading here ^^
        #self.show('project.SelectorScreen')
        main = self.show('presentation.MainScreen')
        if len(argv) > 1:
            main.do_load(argv[1])

        #main.do_publish()
        main.do_edit()

if __name__ in ('__main__', '__android__'):
    PresemtApp().run()
