'''
Scatter plane with grid
'''

from kivy.uix.scatter import ScatterPlane, Scatter
from kivy.properties import NumericProperty, BooleanProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.graphics import Line, Color
from kivy.factory import Factory

from presentation_objects import PlaneObject


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
        # FIXME grid disable cause every line is in a different VBO
        # That's cause lot of lags on many devices. Activate background
        # grid as soon as we will be able to do one call-one draw
        return
        self.canvas.clear()
        gs = self.grid_spacing
        gc = self.grid_count * gs
        count = 0
        with self.canvas:
            Color(.9, .9, .9, .2)
            for x in xrange(-gc, gc, gs):
                Line(points=(x, -gc, x, gc))
                Line(points=(-gc, x, gc, x))
                count += 2


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

        if touch.is_double_tap:
            self.ctrl.selection_points = self.to_local(*touch.pos)
        else:
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
        if touch.grab_current is self:
            if touch.is_double_tap:
                self.ctrl.selection_points.extend(
                    self.to_local(*touch.pos))
                self.ctrl.update_select()
            elif touch in self._touches:
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
        win = self.get_parent_window()
        if not win:
            return False
        cp = self.to_local(*win.center)
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
        # Reserved for further use; e.g. start video playback or whatever
        pass

    def on_scene_leave(self, child):
        # Reserved for further use; e.g. stop video playback or whatever
        pass

    def cull_children(self, *args, **kwargs):
        no_event = kwargs.get('no_event', False)
        # *args cause we use cull_children as a callback for animation's
        # on_progress
        old_children = self.children[:]
        self._really_clear_widgets()

        for child in reversed(self.all_children):
            if self.is_visible(child):
                self._really_add_widget(child)
                if not no_event and not child in old_children:
                    self.dispatch('on_scene_enter', child)
        if no_event:
            return
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
