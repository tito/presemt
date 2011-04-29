'''
Panel for configuration
Panel have open() and close() hook, to know when they are displayed or not
'''

from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.factory import Factory

from config import SUPPORTED_VID, SUPPORTED_IMG

try:
    import android
    user_path = u'/sdcard'
except ImportError:
    user_path = u'~'

def prefix(exts):
    return ['*.' + t for t in exts]


class Panel(FloatLayout):

    ctrl = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.register_event_type('on_open')
        self.register_event_type('on_close')
        super(Panel, self).__init__(**kwargs)

    def on_open(self):
        pass

    def on_close(self):
        pass


class TextStackEntry(Factory.BoxLayout):

    panel = ObjectProperty(None)

    text = StringProperty('')

    ctrl = ObjectProperty(None)

    def on_touch_down(self, touch):
        if super(TextStackEntry, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.ctrl.create_text(touch=touch, text=self.text)
            return True

Factory.register('TextStackEntry', cls=TextStackEntry)

class ImageButton(Factory.ButtonBehavior, Factory.Image):
    pass

Factory.register('ImageButton', cls=ImageButton)

class TextPanel(Panel):

    textinput = ObjectProperty(None)

    stack = ObjectProperty(None)

    status_btn = 'btn_panel_text'

    def add_text(self):
        text = self.textinput.text.strip()
        self.textinput.text = ''
        if not text:
            return
        label = TextStackEntry(text=text, ctrl=self.ctrl, panel=self)
        self.stack.add_widget(label)
        self.ctrl.create_text(text=text)


class LocalFilePanel(Panel):

    path = StringProperty(user_path)

    status_btn = 'btn_panel_image'

    imgtypes = ListProperty(prefix(SUPPORTED_IMG))

    vidtypes = ListProperty(prefix(SUPPORTED_VID))

    suptypes = ListProperty(prefix(SUPPORTED_IMG + SUPPORTED_VID))


