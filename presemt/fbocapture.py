from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, ListProperty
from kivy.graphics import Rectangle, Fbo, Color, Canvas
from kivy.factory import Factory


class FboCapture(FloatLayout):

    texture = ObjectProperty(None)

    texture_thumb = ObjectProperty(None)

    thumb_size = ListProperty([50, 50])

    def __init__(self, **kwargs):
        self.canvas = Canvas()
        with self.canvas:
            self.fbo = Fbo(size=self.size)
        self.fbo_thumb = Fbo(size=self.thumb_size)
        with self.fbo:
            Color(0, 0, 0)
            self.fbo_rect = Rectangle(size=self.size)
        self.texture = self.fbo.texture
        with self.fbo_thumb:
            Color(1, 1, 1)
            self.fbo_thumb_rect = Rectangle(size=self.thumb_size)
        super(FboCapture, self).__init__(**kwargs)

    def on_size(self, instance, value):
        w, h = value
        ratio = float(w) / h
        if w > h:
            w = 160
            h = w / ratio
        else:
            h = 160
            w = h * ratio
        w = max(1, w)
        h = max(1, h)
        self.thumb_size = int(w), int(h)
        self.fbo.size = value
        self.fbo_rect.size = value
        self.texture = self.fbo.texture
        self.fbo_thumb_rect.texture = self.fbo.texture

    def on_thumb_size(self, instance, value):
        self.fbo_thumb.size = value
        self.fbo_thumb_rect.size = value
        self.texture_thumb = self.fbo_thumb.texture

    def add_widget(self, child):
        child.parent = self
        self.children.insert(0, child)
        self.fbo.add(child.canvas)

    def remove_widget(self, child):
        self.children.remove(child)
        self.fbo.remove(child.canvas)

Factory.register('FboCapture', cls=FboCapture)
