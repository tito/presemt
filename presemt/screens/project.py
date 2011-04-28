from . import Screen
from os import listdir
from os.path import join, exists
from datetime import datetime
from functools import partial

from document import Document
from kivy.lang import Builder
from kivy.graphics.texture import Texture

class SelectorScreen(Screen):
    def __init__(self, **kwargs):
        super(SelectorScreen, self).__init__(**kwargs)

    def on_parent(self, instance, value):
        if value:
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
            title=title,
            time=dt.strftime('%d/%m/%y %H:%M'),
            tex0=tex0, tex1=tex1, tex2=tex2,
            slide_count=len(slides),
            obj_count=len(list(doc.objects)),
            func_edit=partial(self.do_edit, filename),
            func_play=partial(self.do_play, filename)
        )
        self.view.add_widget(item)

    def do_edit(self, filename):
        print 'do_edit', filename
        self.app.edit_project(filename)

    def do_play(self, filename):
        print 'do_play', filename
        self.app.play_project(filename)
