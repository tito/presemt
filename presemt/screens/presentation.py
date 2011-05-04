from os.path import splitext
from . import Screen
from document import Document, TextObject, ImageObject, VideoObject
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, ObjectProperty, \
        BooleanProperty, ListProperty, AliasProperty, OptionProperty
from kivy.animation import Animation
from functools import partial
from time import time
from os.path import join
from os import makedirs

from config import SUPPORTED_VID, SUPPORTED_IMG
import presentation_plane
from presentation_panel import TextPanel, LocalFilePanel
from presentation_objects import ImagePlaneObject, VideoPlaneObject, \
    TextPlaneObject
from presentation_slides import Slide

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
# Main screen, act as a controler for everybody
#

class MainScreen(Screen):

    modalquit = ObjectProperty(None, allownone=True)

    def _get_filename(self):
        return self._filename
    def _set_filename(self, filename):
        self._filename = filename
        return True
    filename = AliasProperty(_get_filename, _set_filename)

    return_action = OptionProperty('edit', options=('edit', 'menu'))

    is_edit = BooleanProperty(False)

    is_dirty = BooleanProperty(False)

    plane = ObjectProperty(None)

    config = ObjectProperty(None)

    capture = ObjectProperty(None)

    do_selection = BooleanProperty(False)

    selection_points = ListProperty([0, 0])

    tb_objects = ObjectProperty(None)

    tb_slides = ObjectProperty(None)

    btn_savefile = ObjectProperty(None)

    def __init__(self, **kwargs):
        self._filename = None
        self._initial_load = True
        self._panel = None
        self._panel_text = None
        self._panel_localfile = None
        self._plane_animation = None
        self.trigger_slides = Clock.create_trigger(
            self.update_slides_capture, 1)
        super(MainScreen, self).__init__(**kwargs)

    def on_parent(self, instance, value):
        try:
            # don't do keyboard shorcut on android platform
            import android
            return
        except ImportError:
            pass
        if value is not None:
            Window.bind(on_keyboard=self.on_window_keyboard)
        else:
            Window.unbind(on_keyboard=self.on_window_keyboard)

    def on_window_keyboard(self, window, code, *largs):
        # edit mode
        if self.is_edit:
            if code == 27:
                if self._panel:
                    self.toggle_panel()
                else:
                    self.ask_quit()
                return True

        # publish mode
        else:
            # keyboard shortcut for publish mode
            slide = self.get_selected_slide()
            if not slide:
                return
            # left pad, previous page
            if code in (276, 280):
                slide = self.get_slide_by_index(slide.index - 1)
                self.select_slide(slide)
            # right pad, next page
            elif code in (275, 281):
                slide = self.get_slide_by_index(slide.index + 1)
                self.select_slide(slide)
            # space bar, focus current page
            elif code == 32:
                self.select_slide(slide)
            # back to edit mode
            elif code == 101:
                self.do_edit()
            # escape
            elif code == 27:
                self.ask_quit()
            else:
                return
            return True

    def on_btn_savefile(self, instance, value):
        value.visible = self.is_dirty

    def on_is_dirty(self, instance, value):
        self.btn_savefile.visible = value

    def go_return_action(self):
        if self.return_action == 'menu':
            self.ask_quit(force=True)
        else:
            self.do_edit()

    def leave_quit(self):
        self.remove_widget(self.modalquit)
        self.modalquit = None

    def ask_quit(self, force=False):
        if force is True or not self.is_dirty:
            self.app.show_start()
            return
        if self.is_dirty:
            if self.modalquit:
                self.leave_quit()
            else:
                self.modalquit = modalquit = ModalQuit(app=self)
                self.add_widget(modalquit)
                Animation(alpha=1, d=.5, t='out_cubic').start(modalquit)

    def set_dirty(self):
        if not self.is_edit:
            return
        self.is_dirty = True

    def _create_object(self, cls, touch, **kwargs):
        self.set_dirty()
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
                child.x, child.y, s)

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
            same = self._panel is panel
            if same:
                panel = None
            anim = Animation(width=0, d=.3, t='out_cubic')
            anim.bind(on_complete=partial(self._anim_show_panel, panel))
            anim.start(self.config_container)
            return
        if panel:
            self._anim_show_panel(panel)

    def _anim_show_panel(self, panel, *largs):
        if self._panel:
            self._panel.dispatch('on_close')
            getattr(self, self._panel.status_btn).state = 'normal'
            self.config.remove_widget(self._panel)
        self._panel = panel
        if self._panel:
            self.config.add_widget(self._panel)
            self._panel.dispatch('on_open')
            getattr(self, self._panel.status_btn).state = 'down'
            anim = Animation(width=350, d=.3, t='out_cubic')
            anim.start(self.config_container)

    # used for kv button
    def toggle_text_panel(self):
        self.toggle_panel('text')

    def toggle_localfile_panel(self):
        self.toggle_panel('localfile')

    def toggle_lock(self):
        self.plane.children_locked = not self.plane.children_locked

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
            obj.download_thumb()
            doc.add_slide(obj.slide_pos, obj.slide_rotation,
                          obj.slide_scale, obj.thumb)

        ws = self.app.config.workspace_dir
        if not self.filename:
            project_dir = join(ws, 'project_%d' % time())
            makedirs(project_dir)
            self._filename = join(project_dir, 'project.json')
        doc.save(self.filename)
        self.is_dirty = False

    def on_filename(self, instance, filename):
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
        self.is_dirty = False

    #
    # Presentation
    #
    def _do_initial_load(self):
        for widget in self.container_edit:
            widget.old_parent = widget.parent
            widget.parent.remove_widget(widget)
        for widget in self.container_publish:
            widget.old_parent = widget.parent
            widget.parent.remove_widget(widget)
        self._initial_load = False

    def do_publish(self):
        if self._initial_load:
            self._do_initial_load()
        self.plane.children_locked = True
        for widget in self.container_edit:
            if not widget.parent:
                continue
            widget.old_parent = widget.parent
            widget.parent.remove_widget(widget)
        for widget in self.container_publish:
            widget.old_parent.add_widget(widget)
        self.is_edit = False

    def do_edit(self):
        if self._initial_load:
            self._do_initial_load()
        self.plane.children_locked = False
        for widget in self.container_publish:
            if not widget.parent:
                continue
            widget.old_parent = widget.parent
            widget.parent.remove_widget(widget)
        for widget in self.container_edit:
            widget.old_parent.add_widget(widget)
        self.is_edit = True

    #
    # Objects
    #

    def remove_object(self, obj):
        self.set_dirty()
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
        self.set_dirty()
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
        self.set_dirty()
        self.unselect_slides()
        self.tb_slides.remove_widget(slide)
        self.update_slide_index()

    def select_slide(self, slide):
        k = {'d': .5, 't': 'out_cubic'}

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
        self.selection_points = [0, 0]
        self.reset_animation()
        self.unselect_slides()

    def get_selected_slide(self):
        for child in self.tb_slides.children:
            if child.selected:
                return child
        if len(self.tb_slides.children):
            return self.tb_slides.children[0]

    def get_slide_by_index(self, index):
        index = index % len(self.tb_slides.children)
        for x in self.tb_slides.children:
            if x.index == index:
                return x

    def go_next_slide(self):
        slide = self.get_selected_slide()
        if not slide:
            return
        self.select_slide(self.get_slide_by_index(slide.index + 1))

    def go_previous_slide(self):
        slide = self.get_selected_slide()
        if not slide:
            return
        self.select_slide(self.get_slide_by_index(slide.index - 1))

    def unselect_slides(self):
        for child in self.tb_slides.children:
            child.selected = False

    def update_slide_index(self):
        for idx, slide in enumerate(reversed(self.tb_slides.children)):
            slide.index = idx

    def update_slides_capture(self, *largs):
        if not self.is_edit:
            return
        pos = self.plane.pos
        scale = self.plane.scale
        rotation = self.plane.rotation
        for slide in self.tb_slides.children:
            self.plane.scale = slide.slide_scale
            self.plane.rotation = slide.slide_rotation
            self.plane.pos = slide.slide_pos
            self.plane.cull_children(no_event=True)
            slide.update_capture()
        self.plane.scale = scale
        self.plane.rotation = rotation
        self.plane.pos = pos
        self.plane.cull_children(no_event=True)


class ModalQuit(FloatLayout):

    alpha = NumericProperty(0.)

    app = ObjectProperty(None)

    def on_touch_down(self, touch):
        super(ModalQuit, self).on_touch_down(touch)
        return True

Factory.register('ModalQuit', cls=ModalQuit)


