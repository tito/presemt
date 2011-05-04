from . import Screen
from os import listdir
from os.path import join, exists
from datetime import datetime

from document import Document
from kivy.lang import Builder
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout

class Modal(FloatLayout):
    alpha = NumericProperty(0.)
    app = ObjectProperty(None)
    def on_touch_down(self, touch):
        super(Modal, self).on_touch_down(touch)
        return True

class ModalSelect(Modal):
    filename = StringProperty(None)

class ModalConfirm(Modal):
    filename = StringProperty(None)

class ModalHelp(Modal):
    pass

class SelectorScreen(Screen):

    modalselect = ObjectProperty(None, allownone=True)

    modalconfirm = ObjectProperty(None, allownone=True)

    modalhelp = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super(SelectorScreen, self).__init__(**kwargs)

    def on_parent(self, instance, value):
        if value:
            self.refresh()

    def ask_load(self, filename):
        if self.modalselect:
            self.leave_load()
        else:
            self.modalselect = modalselect = ModalSelect(
                app=self, filename=filename)
            self.add_widget(modalselect)
            Animation(alpha=1, d=.5, t='out_cubic').start(modalselect)

    def leave_load(self):
        if not self.modalselect:
            return
        self.remove_widget(self.modalselect)
        self.modalselect = None

    def show_help(self):
        if self.modalhelp:
            return
        self.modalhelp = modalhelp = ModalHelp(app=self)
        self.add_widget(modalhelp)
        Animation(alpha=1, d=.5, t='out_cubic').start(modalhelp)

    def leave_help(self):
        if not self.modalhelp:
            return
        self.remove_widget(self.modalhelp)
        self.modalhelp = None


    def delete_project(self, filename, force=False):
        if force:
            self.app.delete_project(filename)
            self.refresh()
            self.leave_load()
            self.leave_delete()
        else:
            self.ask_delete(filename)

    def leave_delete(self):
        if not self.modalconfirm:
            return
        self.remove_widget(self.modalconfirm)
        self.modalconfirm = None

    def ask_delete(self, filename):
        if self.modalconfirm:
            self.leave_delete()
        else:
            self.modalconfirm = modalconfirm = ModalConfirm(
                app=self, filename=filename)
            self.add_widget(modalconfirm)
            Animation(alpha=1, d=.5, t='out_cubic').start(modalconfirm)

    def refresh(self):
        self.view.clear_widgets()
        self.search_documents()

    def search_documents(self):
        ws = self.app.config.workspace_dir
        if not exists(ws):
            return
        docs = []
        for item in listdir(ws):
            fn = join(ws, item, 'project.json')
            if not exists(fn):
                continue
            doc = Document()
            doc.load(fn)
            docs.append((doc, fn))

        docs.sort(lambda a, b: cmp(a[0].infos.time_modification, b[0].infos.time_modification))
        for doc, filename in docs:
            self.load_document(doc, filename)

    def load_document(self, doc, filename):
        view = self.view

        def thumb_texture(thumb):
            w, h, pixels = thumb
            texture = Texture.create((w, h), 'rgb', 'ubyte')
            texture.blit_buffer(pixels, colorfmt='rgb')
            return texture

        slides = list(doc.slides)
        title = ''
        texs = [thumb_texture(s.thumb) for s in slides[0:3]]
        texs.extend([None, None, None])
        tex0, tex1, tex2 = texs[0:3]
        dt = datetime.fromtimestamp(doc.infos.time_modification)

        if tex0 is None:
            title = 'No preview available'

        item = Builder.template('SelectorItem',
            app=self,
            title=title,
            time=dt.strftime('%d/%m/%y %H:%M'),
            tex0=tex0, tex1=tex1, tex2=tex2,
            slide_count=len(slides),
            obj_count=len(list(doc.objects)),
            filename=filename)
        self.view.add_widget(item)

    def do_edit(self, filename):
        self.leave_load()
        print 'do_edit', filename
        self.app.edit_project(filename)

    def do_play(self, filename):
        self.leave_load()
        print 'do_play', filename
        self.app.play_project(filename)
