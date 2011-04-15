from tempfile import mktemp
from math import sqrt
from os.path import join, dirname, splitext
from os import unlink
from . import Screen
from document import Document, TextObject, ImageObject, VideoObject
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

    def add_text(self):
        text = self.textinput.text.strip()
        self.textinput.text = ''
        if not text:
            return
        label = TextStackEntry(text=text, ctrl=self.ctrl, panel=self)
        self.stack.add_widget(label)
        self.ctrl.create_text(text=text)


class LocalFilePanel(Panel):
    imgtypes = ListProperty(prefix(SUPPORTED_IMG))
    vidtypes = ListProperty(prefix(SUPPORTED_VID))
    suptypes = ListProperty(prefix(SUPPORTED_IMG + SUPPORTED_VID))


#
# Objects that will be added on the plane
#

class PlaneObject(Scatter):

    selected = BooleanProperty(False)

    ctrl = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PlaneObject, self).__init__(**kwargs)
        touch = kwargs.get('touch_follow', None)
        if touch:
            touch.ud.scatter_follow = self
            touch.grab(self)

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

    font_size = NumericProperty(48)


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


#
# Main screen, act as a controler for everybody
#

class MainScreen(Screen):

    plane = ObjectProperty(None)

    config = ObjectProperty(None)

    capture = ObjectProperty(None)

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

    def _create_object(self, cls, touch, **kwargs):
        kwargs.setdefault('rotation', -self.plane.rotation)
        kwargs.setdefault('scale', 1. / self.plane.scale)
        obj = cls(touch_follow=touch, ctrl=self, **kwargs)
        if 'size' in kwargs:
            obj.size = kwargs.get('size')
        if 'scale' in kwargs:
            obj.rotation = kwargs.get('scale')
        if 'rotation' in kwargs:
            obj.rotation = kwargs.get('rotation')
        if 'pos' in kwargs:
            obj.pos = kwargs.get('pos')
        else:
            obj.pos = self.plane.to_local(*self.center)
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

    def create_text(self, touch=None, **kwargs):
        self._create_object(TextPlaneObject, touch, **kwargs)

    def from_localfile(self, touch, **kwargs):
        kwargs.setdefault('do_adjust', True)
        source = kwargs['source']
        ext = splitext(source)[-1][1:]
        if ext in SUPPORTED_IMG:
            self.create_image(touch, **kwargs)
        elif ext in SUPPORTED_VID:
            self.create_video(touch, **kwargs)

    def create_image(self, touch=None, **kwargs):
        self._create_object(ImagePlaneObject, touch, **kwargs)

    def create_video(self, touch=None, **kwargs):
        self._create_object(VideoPlaneObject, touch, **kwargs)

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
        doc = Document(size=self.size, pos=self.plane.pos,
                       scale=self.plane.scale, rotation=self.plane.rotation)
        for obj in reversed(self.plane.all_children):
            attrs = [ ('pos', obj.pos), ('size', obj.size),
                ('rotation', obj.rotation), ('scale', obj.scale)]
            if isinstance(obj, TextPlaneObject):
                attrs += [(attr, getattr(obj, attr)) for attr in TextObject.__attrs__]
                doc.create_text(**dict(attrs))
            elif isinstance(obj, ImagePlaneObject):
                attrs += [(attr, getattr(obj, attr)) for attr in ImageObject.__attrs__]
                doc.create_image(**dict(attrs))
            elif isinstance(obj, VideoPlaneObject):
                attrs += [(attr, getattr(obj, attr)) for attr in VideoObject.__attrs__]
                doc.create_video(**dict(attrs))

        for obj in reversed(self.tb_slides.children):
            doc.add_slide(obj.slide_pos, obj.slide_rotation,
                          obj.slide_scale, obj.thumb)

        doc.save('output.json')

    def do_load(self, filename):
        doc = Document()
        doc.load(filename)
        self.plane.size = doc.infos.root_size
        self.plane.scale = doc.infos.root_scale
        self.plane.rotation = doc.infos.root_rotation
        self.plane.pos = doc.infos.root_pos
        for obj in doc.objects:
            attrs = [ ('pos', obj.pos), ('size', obj.size),
                ('rotation', obj.rotation), ('scale', obj.scale)]
            if obj.dtype == 'text':
                attrs += [(attr, obj[attr]) for attr in TextObject.__attrs__]
                self.create_text(**dict(attrs))
            elif obj.dtype == 'image':
                attrs += [(attr, obj[attr]) for attr in ImageObject.__attrs__]
                self.create_image(**dict(attrs))
            elif obj.dtype == 'video':
                attrs += [(attr, obj[attr]) for attr in VideoObject.__attrs__]
                self.create_video(**dict(attrs))
        for obj in doc.slides:
            self.create_slide(pos=obj.pos, rotation=obj.rotation,
                              scale=obj.scale, thumb=obj.thumb)

    #
    # Objects
    #

    def remove_object(self, obj):
        self.plane.remove_widget(obj)

    def configure_object(self, obj):
        # FIXME TODO
        pass

    #
    # Slides
    #

    def reset_animation(self):
        if not self._plane_animation:
            return
        self._plane_animation.stop(self.plane)
        self._plane_animation = None

    def create_slide(self, pos=None, rotation=None, scale=None, thumb=None):
        plane = self.plane
        pos = pos or plane.pos
        scale = scale or plane.scale
        rotation = rotation or plane.rotation

        slide = Slide(ctrl=self,
                      slide_pos=pos,
                      slide_rotation=rotation,
                      slide_scale=scale,
                      thumb=thumb)
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
        self._plane_animation.bind(on_complete=slide.update_capture)
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

    '''
    def update_slides_capture(self, *largs):
        pos = self.plane.pos
        scale = self.plane.scale
        rotation = self.plane.rotation
        for slide in self.tb_slides.children:
            self.plane.scale = slide.slide_scale
            self.plane.rotation = slide.slide_rotation
            self.plane.pos = slide.slide_pos
            self.plane.canvas.ask_update()
            slide.update_capture()
        self.plane.scale = scale
        self.plane.rotation = rotation
        self.plane.pos = pos
    '''

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
    def __init__(self, **kwargs):
        self.thumb = kwargs.get('thumb', None)
        del kwargs['thumb']
        self.ctrl = kwargs.get('ctrl')
        if self.thumb:
            self.upload_thumb()
        else:
            self.update_capture()
        super(Slide, self).__init__(**kwargs)
    def update_capture(self, *largs):
        from kivy.graphics.opengl import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE
        from kivy.graphics.texture import Texture
        fbo = self.ctrl.capture.fbo_thumb
        fbo.ask_update()
        fbo.draw()
        fbo.bind()
        tmp = glReadPixels(0, 0, fbo.size[0], fbo.size[1], GL_RGBA, GL_UNSIGNED_BYTE)
        fbo.release()
        texture = Texture.create(fbo.size, 'rgb', 'ubyte')
        texture.blit_buffer(tmp, colorfmt='rgba')
        self.texture = texture
        self.texture_size = texture.size
        self.thumb = (fbo.size[0], fbo.size[1], tmp)
    def upload_thumb(self):
        from kivy.graphics.texture import Texture
        w, h, pixels = self.thumb
        texture = Texture.create((w, h), 'rgba', 'ubyte')
        texture.blit_buffer(pixels, colorfmt='rgba')
        self.texture = texture
        self.texture_size = texture.size



#
# Scatter plane with grid
#

from kivy.graphics import Canvas, Fbo, Rectangle

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

class MainPlane(ScatterPlane):

    grid_spacing = NumericProperty(50)

    grid_count = NumericProperty(1000)

    children_locked = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._trigger_grid = Clock.create_trigger(self.fill_grid, -1)
        self._trigger_cull = Clock.create_trigger(self.cull_children, -1)
        super(MainPlane, self).__init__(**kwargs)
        self.register_event_type('on_scene_enter')
        self.register_event_type('on_scene_leave')
        self.all_children = []
        self._trigger_grid()
        self._trigger_cull()

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
        w_win_center = w.to_window(*w.pos)
        lwc = self.to_local(*w_win_center)
        # XXX Why does this not work instead of the previous two?
        #lwc = w.to_parent(*w.center)
        corner = w.to_parent(-w.width / 2., -w.height / 2.)
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
        self._trigger_cull()
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
        self._trigger_cull()

    def remove_widget(self, child):
        self.all_children.remove(child)
        self._really_remove_widget(child)
        self._trigger_cull()

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
