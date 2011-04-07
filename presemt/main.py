'''
PresMT - A presentation software
================================
'''

import kivy
kivy.require('1.0.5')

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout


class PresemtApp(App):
    def __init__(self):
        super(PresemtApp, self).__init__()
        self.screens = {}

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

    def build(self):
        self.root = FloatLayout()
        self.show('loading.LoadingScreen')
        # ... do loading here ^^
        self.show('project.SelectorScreen')

if __name__ in ('__main__', '__android__'):
    PresemtApp().run()
