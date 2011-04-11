from os.path import join, dirname
from . import Screen
from kivy.uix.scatter import ScatterPlane, Scatter
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.factory import Factory
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

default_image = join(dirname(__file__), '..', 'data', 'tests', 'faust_github.jpg')

class PlaneObject(Scatter):

    def __init__(self, **kwargs):
        super(PlaneObject, self).__init__(**kwargs)
        touch = kwargs.get('touch_follow', None)
        if touch:
            touch.ud.scatter_follow = self
            touch.grab(self)

    def configure(self):
        # call the configuration interface for the object
        print 'show configure interface'

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.is_double_tap:
            self.configure()
        return super(PlaneObject, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if 'scatter_follow' in touch.ud:
                self.center = touch.pos
        return super(PlaneObject, self).on_touch_move(touch)


class TextPlaneObject(PlaneObject):

    text = StringProperty('Hello world')

    font_size = NumericProperty(120)


class ImagePlaneObject(PlaneObject):

    source = StringProperty(default_image)


class VideoPlaneObject(PlaneObject):

    source = StringProperty(None)


class MainScreen(Screen):

    plane = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

    def _create_object(self, cls, touch, pos):
        if touch:
            pos = self.plane.to_local(*touch.pos)
        obj = cls(touch_follow=touch)
        if pos:
            obj.center = pos
        self.plane.add_widget(obj)

    def create_text(self, touch=None, pos=None):
        self._create_object(TextPlaneObject, touch, pos)

    def create_image(self, touch=None, pos=None):
        self._create_object(ImagePlaneObject, touch, pos)

    def create_video(self, touch=None, pos=None):
        self._create_object(VideoPlaneObject, touch, pos)


class MainPlane(ScatterPlane):

    grid_spacing = NumericProperty(50)

    grid_count = NumericProperty(1000)

    def __init__(self, **kwargs):
        super(MainPlane, self).__init__(**kwargs)
        self.bind(
            grid_spacing=self._trigger_grid,
            grid_count=self._trigger_grid)
        self._trigger_grid()

    def _trigger_grid(self, *largs):
        Clock.unschedule(self.fill_grid)
        Clock.schedule_once(self.fill_grid)

    def fill_grid(self, *largs):
        self.canvas.clear()
        gs = self.grid_spacing
        gc = self.grid_count * gs
        with self.canvas:
            Color(.1, .1, .1, .9)
            for x in xrange(-gc, gc, gs):
                Line(points=(x, -gc, x, gc))
                Line(points=(-gc, x, gc, x))

Factory.register('MainPlane', cls=MainPlane)
