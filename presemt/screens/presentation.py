from tempfile import mktemp
from math import sqrt
from os.path import join, dirname, splitext
from os import unlink
from . import Screen
from kivy.core.window import Window
from kivy.vector import Vector
from kivy.uix.scatter import ScatterPlane, Scatter
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.factory import Factory
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, \
        BooleanProperty, ListProperty
from kivy.animation import Animation
from kivy.core.image import ImageLoader
from kivy.lang import Builder


def prefix(exts):
    return ['*.' + t for t in exts]

SUPPORTED_IMG = []
for loader in ImageLoader.loaders:
    for ext in loader.extensions():
        if ext not in SUPPORTED_IMG:
            SUPPORTED_IMG.append(ext)
# OK, who has a better idea on how to do that that is still acceptable?
SUPPORTED_VID = ['avi', 'mpg', 'mpeg']


def point_inside_polygon(x,y,poly):
    '''Taken from http://www.ariel.com.au/a/python-point-int-poly.html'''

    n = len(poly)
    inside = False

    p1x = poly[0]
    p1y = poly[1]
    for i in xrange(0, n+2, 2):
        p2x = poly[i % n]
        p2y = poly[(i+1) % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

#
# Panel for configuration
# Panel have open() and close() hook, to know when they are displayed or not
#

class Panel(FloatLayout):
    ctrl = ObjectProperty(None)
    def open(self):
        pass
    def close(self):
        pass


class TextStackEntry(Factory.BoxLayout):
    panel = ObjectProperty(None)
    text = StringProperty('')
    ctrl = ObjectProperty(None)
    def on_touch_down(self, touch):
        if super(TextStackEntry, self).on_touch_down(touch):
            return True
        pos = self.ctrl.center
        self.ctrl.create_text(touch=touch, pos=pos, text=self.text)

Factory.register('TextStackEntry', cls=TextStackEntry)

class ImageButton(Factory.ButtonBehavior, Factory.Image):
    pass

Factory.register('ImageButton', cls=ImageButton)

class TextPanel(Panel):

    textinput = ObjectProperty(None)

    stack = ObjectProperty(None)

    def add_text(self):
        text = self.textinput.text.strip()
        self.textinput.text = ''
        if not text:
            return
        label = TextStackEntry(text=text, ctrl=self.ctrl, panel=self)
        self.stack.add_widget(label)


class LocalFilePanel(Panel):
    imgtypes = ListProperty(prefix(SUPPORTED_IMG))
    vidtypes = ListProperty(prefix(SUPPORTED_VID))
    suptypes = ListProperty(prefix(SUPPORTED_IMG + SUPPORTED_VID))


#
# Objects that will be added on the plane
#

class PlaneObject(Scatter):

    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(PlaneObject, self).__init__(**kwargs)
        touch = kwargs.get('touch_follow', None)
        if touch:
            touch.ud.scatter_follow = self
            touch.grab(self)

    def configure(self):
        pass

    def get_configure(self):
        pass

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

    font_size = NumericProperty(48)

    def get_configure(self):
        from kivy.uix.button import Button
        return Button(text='Hello World')


class ImagePlaneObject(PlaneObject):

    source = StringProperty(None)


class VideoPlaneObject(PlaneObject):

    source = StringProperty(None)


#
# Main screen, act as a controler for everybody
#

class MainScreen(Screen):

    plane = ObjectProperty(None)

    config = ObjectProperty(None)

    do_selection = BooleanProperty(False)

    selection_points = ListProperty([0, 0])

    tb_objects = ObjectProperty(None)

    tb_slides = ObjectProperty(None)

    def __init__(self, **kwargs):
        self._panel = None
        self._panel_text = None
        self._panel_localfile = None
        self._plane_animation = None
        super(MainScreen, self).__init__(**kwargs)

    def _create_object(self, cls, touch, pos, **kwargs):
        kwargs.setdefault('rotation', -self.plane.rotation)
        kwargs.setdefault('scale', 1. / self.plane.scale)
        obj = cls(touch_follow=touch, **kwargs)
        if pos:
            pos = self.plane.to_local(*pos)
            obj.center = pos
        self.plane.add_widget(obj)

    def update_select(self):
        s = self.selection_points
        for child in self.plane.children:
            child.selected = point_inside_polygon(
                child.center_x, child.center_y, s)

    def selection_align(self):
        childs = [x for x in self.plane.children if x.selected]
        if not childs:
            return
        # do align on x
        left = min([x.x for x in childs])
        right = max([x.right for x in childs])
        middle = left + (right - left) / 2.
        for child in childs:
            child.center_x = middle

    def cancel_selection(self):
        self.do_selection = False
        self.selection_points = [0, 0]
        for child in self.plane.children:
            child.selected = False

    def create_text(self, touch=None, pos=None, **kwargs):
        self._create_object(TextPlaneObject, touch, pos, **kwargs)

    def from_localfile(self, touch, **kwargs):
        source = kwargs['source']
        ext = splitext(source)[-1][1:]
        if ext in SUPPORTED_IMG:
            self.create_image(touch, **kwargs)
        elif ext in SUPPORTED_VID:
            self.create_video(touch, **kwargs)

    def create_image(self, touch=None, pos=None, **kwargs):
        pos = self.center
        self._create_object(ImagePlaneObject, touch, pos, **kwargs)

    def create_video(self, touch=None, pos=None, **kwargs):
        pos = self.center
        self._create_object(VideoPlaneObject, touch, pos, **kwargs)

    def get_text_panel(self):
        if not self._panel_text:
            self._panel_text = TextPanel(ctrl=self)
        return self._panel_text

    def get_localfile_panel(self):
        if not self._panel_localfile:
            self._panel_localfile = LocalFilePanel(ctrl=self)
        return self._panel_localfile

    def toggle_panel(self, name=None):
        panel = None
        if name:
            panel = getattr(self, 'get_%s_panel' % name)()
        if self._panel:
            self._panel.close()
            self.config.remove_widget(self._panel)
            same = self._panel is panel
            self._panel = None
            if same:
                return
        if panel:
            self._panel = panel
            self.config.add_widget(panel)
            self._panel.open()

    # used for kv button
    def toggle_text_panel(self):
        self.toggle_panel('text')

    def toggle_localfile_panel(self):
        self.toggle_panel('localfile')

    def toggle_lock(self):
        self.plane.children_locked = not self.plane.children_locked

    #
    # Navigation
    #

    def go_home(self):
        self.app.show('project.SelectorScreen')

    #
    # Save/Load
    #

    def do_save(self):
        pass

    #
    # Slides
    #

    def reset_animation(self):
        if not self._plane_animation:
            return
        self._plane_animation.stop(self.plane)
        self._plane_animation = None

    def add_slide(self):
        plane = self.plane
        fn = mktemp('.jpg')
        Window.screenshot(fn)
        slide = Slide(source=fn, ctrl=self,
                      slide_pos=plane.pos,
                      slide_rotation=plane.rotation,
                      slide_scale=plane.scale)
        unlink(fn)
        self.tb_slides.add_widget(slide)
        self.update_slide_index()

    def remove_slide(self, slide):
        self.unselect_slides()
        self.tb_slides.remove_widget(slide)
        self.update_slide_index()

    def select_slide(self, slide):
        print 'rotation', slide.slide_rotation, self.plane.rotation
        print 'scale', slide.slide_scale
        print 'pos', slide.slide_pos
        k = {'d': .5, 't': 'out_quad'}

        # highlight slide
        self.unselect()
        slide.selected = True

        # rotation must be fixed by hand
        slide_rotation = slide.slide_rotation
        s = abs(slide_rotation - self.plane.rotation)
        if s > 180:
            if slide_rotation > self.plane.rotation:
                slide_rotation -= 360
            else:
                slide_rotation += 360

        # move to the correct position in the place
        self._plane_animation = Animation(pos=slide.slide_pos,
                 rotation=slide_rotation,
                 scale=slide.slide_scale, **k)
        self._plane_animation.bind(on_progress=self.plane.cull_children)
        self._plane_animation.start(self.plane)

    def unselect(self):
        self.reset_animation()
        self.unselect_slides()

    def unselect_slides(self):
        for child in self.tb_slides.children:
            child.selected = False

    def update_slide_index(self):
        for idx, slide in enumerate(reversed(self.tb_slides.children)):
            slide.index = idx


class Slide(Factory.ButtonBehavior, Factory.Image):
    ctrl = ObjectProperty(None)
    slide_rotation = NumericProperty(0)
    slide_scale = NumericProperty(1.)
    slide_pos = ListProperty([0,0])
    selected = BooleanProperty(False)
    index = NumericProperty(0)
    def on_press(self, touch):
        if touch.is_double_tap:
            self.ctrl.remove_slide(self)
        else:
            self.ctrl.select_slide(self)


#
# Scatter plane with grid
#

class MainPlane(ScatterPlane):

    grid_spacing = NumericProperty(50)

    grid_count = NumericProperty(1000)

    children_locked = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(MainPlane, self).__init__(**kwargs)
        self.bind(
            grid_spacing=self._trigger_grid,
            grid_count=self._trigger_grid)
        self._trigger_grid()
        self.register_event_type('on_scene_enter')
        self.register_event_type('on_scene_leave')
        self.all_children = []

    def _trigger_grid(self, *largs):
        Clock.unschedule(self.fill_grid)
        Clock.schedule_once(self.fill_grid)

    def fill_grid(self, *largs):
        self.canvas.clear()
        gs = self.grid_spacing
        gc = self.grid_count * gs
        with self.canvas:
            Color(.9, .9, .9, .2)
            for x in xrange(-gc, gc, gs):
                Line(points=(x, -gc, x, gc))
                Line(points=(-gc, x, gc, x))


    #
    # In order to maneuver more easily with a lot of widgets on the screen, we
    # want to be able to lock the children. Since we still want to handle the
    # touch events ourselves as if there were no children, we must overload the
    # on_touch_* handlers and do almost the same that our parent class does,
    # except that we only propagate the on_touch_* events to our children if
    # self.children_locked is False.
    #

    def on_touch_down(self, touch):
        x, y = touch.x, touch.y

        if not self.children_locked:
            # let the child widgets handle the event if they want
            touch.push()
            touch.apply_transform_2d(self.to_local)
            if super(Scatter, self).on_touch_down(touch):
                touch.pop()
                return True
            touch.pop()

        # grab the touch so we get all it later move events for sure
        touch.grab(self)
        self._touches.append(touch)
        self._last_touch_pos[touch] = touch.pos

        return True

    def on_touch_move(self, touch):
        x, y = touch.x, touch.y
        if not self.children_locked:
            # let the child widgets handle the event if they want
            if not touch.grab_current == self:
                touch.push()
                touch.apply_transform_2d(self.to_local)
                if super(Scatter, self).on_touch_move(touch):
                    touch.pop()
                    return True
                touch.pop()

        # rotate/scale/translate
        if touch in self._touches and touch.grab_current == self:
            self.transform_with_touch(touch)
            self._last_touch_pos[touch] = touch.pos

        return True

    def on_touch_up(self, touch):
        x, y = touch.x, touch.y
        if not self.children_locked:
            # if the touch isnt on the widget we do nothing, just try children
            if not touch.grab_current == self:
                touch.push()
                touch.apply_transform_2d(self.to_local)
                if super(Scatter, self).on_touch_up(touch):
                    touch.pop()
                    return True
                touch.pop()

        # remove it from our saved touches
        if touch in self._touches and touch.grab_state:
            touch.ungrab(self)
            del self._last_touch_pos[touch]
            self._touches.remove(touch)

        return True

    #
    # Culling below
    #

    def is_visible(self, w):
        '''
        Determine if planeobject w (a scatter itself) is visible in the current
        scatterplane viewport. Uses bounding circle check.
        '''
        # Get minimal bounding circle around widget
        w_win_center = w.to_window(*w.center)
        lwc = self.to_local(*w_win_center)
        # XXX Why does this not work instead of the previous two?
        #lwc = w.to_parent(*w.center)
        corner = w.to_parent(0, 0)
        r = Vector(*lwc).distance(Vector(*corner))

        # Get minimal bounding circle around viewport
        # TODO If an optimization is required
        cp = self.to_local(*Window.center)
        #ww, wh = Window.size
        #topright = self.to_local(ww, wh)
        botleft = self.to_local(0, 0)
        wr = Vector(*cp).distance(botleft)

        dist = Vector(*cp).distance(Vector(lwc))
        if dist - r <= wr:
            return True
        return False

    def transform_with_touch(self, touch):
        #import pdb; pdb.set_trace()
        self.cull_children()
        super(MainPlane, self).transform_with_touch(touch)

    def on_scene_enter(self, child):
        print 'entering:', child

    def on_scene_leave(self, child):
        print 'leaving:', child

    def cull_children(self, *args):
        # *args cause we use cull_children as a callback for animation's
        # on_progress
        old_children = self.children[:]
        self._really_clear_widgets()

        for child in reversed(self.all_children):
            if self.is_visible(child):
                self._really_add_widget(child)
                if not child in old_children:
                    self.dispatch('on_scene_enter', child)
        for child in old_children:
            if child not in self.children:
                self.dispatch('on_scene_leave', child)

    def add_widget(self, child):
        assert isinstance(child, PlaneObject)

        self.all_children.insert(0, child)
        self._really_add_widget(child, front=True)

    def remove_widget(self, child):
        self.all_children.remove(child)
        self._really_remove_widget(child)

    def clear_widgets(self):
        self.all_children = []
        self._really_clear_widgets()

    def _really_add_widget(self, child, front=False):
        child.parent = self
        self.children.insert(0, child)
        self.canvas.add(child.canvas)

    def _really_remove_widget(self, child):
        self.children.remove(child)
        self.canvas.remove(child.canvas)

    def _really_clear_widgets(self):
        for child in self.children[:]:
            self._really_remove_widget(child)


Factory.register('MainPlane', cls=MainPlane)
