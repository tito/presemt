from kivy.factory import Factory
from kivy.properties import BooleanProperty, ObjectProperty


class ButtonBehavior(object):
    '''Button behavior.

    :Events:
        `on_press`:
            Fired when a touch is pressing the widget
        `on_release`:
            Fired when the first touch is up
    '''

    is_hover = BooleanProperty(False)

    button_grab = BooleanProperty(False)

    button_touch = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super(ButtonBehavior, self).__init__(**kwargs)
        self.register_event_type('on_press')
        self.register_event_type('on_release')
        self.bind(
            on_touch_down=self._button_on_touch_down,
            on_touch_up=self._button_on_touch_up)

    def on_press(self, touch):
        pass

    def on_release(self, touch):
        pass

    def _button_on_touch_down(self, instance, touch):
        if not self.collide_point(*touch.pos):
            return
        touch.ungrab(self)
        touch.grab(self)
        self.is_hover = True
        self.button_touch = touch
        self.dispatch('on_press', touch)
        return self.button_grab

    def _button_on_touch_up(self, instance, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        self.is_hover = False
        self.dispatch('on_release', touch)
        self.button_touch = None
        return self.button_grab

Factory.register('ButtonBehavior', cls=ButtonBehavior)


class HoverBehavior(object):
    '''Hover behavior, but not used right now.'
    '''

    is_hover = BooleanProperty(False)

    hover_grab = BooleanProperty(False)

    def __init__(self, **kwargs):
        self._hover_touch = None
        super(HoverBehavior, self).__init__(**kwargs)
        self.bind(
            on_touch_down=self._hover_on_touch_down,
            on_touch_move=self._hover_on_touch_move,
            on_touch_up=self._hover_on_touch_up)

    def _hover_on_touch_down(self, instance, touch):
        if self._hover_touch:
            return
        if not self.collide_point(*touch.pos):
            return
        touch.ungrab(self)
        touch.grab(self)
        self._hover_touch = touch
        self.is_hover = True
        return self.hover_grab

    def _hover_on_touch_move(self, instance, touch):
        if touch.grab_current is not self:
            return
        self.is_hover = self.collide_point(*touch.pos)
        return self.hover_grab

    def _hover_on_touch_up(self, instance, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        self.is_hover = False
        self._hover_touch = None
        return self.hover_grab

Factory.register('HoverBehavior', cls=HoverBehavior)

