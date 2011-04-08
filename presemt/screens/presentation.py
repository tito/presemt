from . import Screen
from kivy.uix.scatter import ScatterPlane
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.factory import Factory
from kivy.properties import NumericProperty


class MainScreen(Screen):
    pass


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
