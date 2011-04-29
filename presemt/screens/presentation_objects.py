'''
Objects that will be added on the plane
'''

from kivy.uix.scatter import Scatter
from kivy.properties import BooleanProperty, ObjectProperty, \
        StringProperty, ListProperty, NumericProperty

class PlaneObject(Scatter):

    selected = BooleanProperty(False)

    ctrl = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PlaneObject, self).__init__(**kwargs)
        touch = kwargs.get('touch_follow', None)
        if touch:
            touch.ud.scatter_follow = self
            touch.grab(self)
        self.bind(transform=self._on_transform)

    def _on_transform(self, instance, value):
        if self.ctrl:
            self.ctrl.set_dirty()

    def collide_point(self, x, y):
        x, y = self.to_local(x, y)
        w2 = self.width / 2.
        h2 = self.height / 2.
        return -w2 <= x <= w2 and -h2 <= y <= h2

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.is_double_tap:
                self.ctrl.remove_object(self)
                return True
            else:
                self.ctrl.configure_object(self)
        return super(PlaneObject, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if 'scatter_follow' in touch.ud:
                self.pos = touch.pos
        return super(PlaneObject, self).on_touch_move(touch)


class TextPlaneObject(PlaneObject):

    text = StringProperty('Hello world')

    bold = BooleanProperty(False)

    italic = BooleanProperty(False)

    color = ListProperty([1, 1, 1, 1])

    font_name = StringProperty(None)

    font_size = NumericProperty(96)


class MediaPlaneObject(PlaneObject):

    source = StringProperty(None)

    do_adjust = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(MediaPlaneObject, self).__init__(**kwargs)

    def on_size(self, instance, value):
        if not self.do_adjust:
            return
        self.scale = min(1, 1. / (max(1, self.width, self.height) / (640. / self.ctrl.plane.scale)))



class ImagePlaneObject(MediaPlaneObject):
    pass

class VideoPlaneObject(MediaPlaneObject):
    pass

