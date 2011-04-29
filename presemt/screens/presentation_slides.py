from kivy.factory import Factory
from kivy.properties import ObjectProperty, NumericProperty, \
        ListProperty, BooleanProperty
from kivy.graphics import Fbo, Rectangle, Color
from kivy.graphics.opengl import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE


class Slide(Factory.ButtonBehavior, Factory.Image):

    ctrl = ObjectProperty(None)

    slide_rotation = NumericProperty(0)

    slide_scale = NumericProperty(1.)

    slide_pos = ListProperty([0,0])

    selected = BooleanProperty(False)

    index = NumericProperty(0)

    def __init__(self, **kwargs):
        # get raw rgb thumb is available
        self.thumb = kwargs.get('thumb', None)
        del kwargs['thumb']
        # extract controler now, we need it.
        self.ctrl = kwargs.get('ctrl')
        # create fbo for tiny texture
        self.fbo = Fbo(size=(160, 120))
        with self.fbo:
            Color(1, 1, 1)
            Rectangle(size=self.fbo.size)
            self.fborect = Rectangle(size=self.fbo.size)
        if self.thumb:
            self.upload_thumb()
        else:
            self.update_capture()
        super(Slide, self).__init__(**kwargs)

    def on_press(self, touch):
        if touch.is_double_tap:
            self.ctrl.remove_slide(self)
        else:
            self.ctrl.select_slide(self)

    def update_capture(self, *largs):
        edit_mode = self.ctrl.is_edit
        self.ctrl.is_edit = False

        # update main fbo
        fbo = self.ctrl.capture.fbo
        fbo.ask_update()
        fbo.draw()

        # update our tiny fbo
        self.fborect.texture = fbo.texture
        self.fbo.ask_update()
        self.fbo.draw()

        # then bind the texture to our texture image
        self.texture = self.fbo.texture
        self.texture_size = self.texture.size

        self.ctrl.is_edit = edit_mode
        self.ctrl.set_dirty()
        self.thumb = None

    def download_thumb(self):
        if self.thumb is None:
            fbo = self.fbo
            fbo.draw()
            fbo.bind()
            tmp = glReadPixels(0, 0, fbo.size[0], fbo.size[1], GL_RGBA, GL_UNSIGNED_BYTE)
            fbo.release()
            # remove alpha
            tmp = list(tmp)
            del tmp[3::4]
            tmp = ''.join(tmp)
            self.thumb = (fbo.size[0], fbo.size[1], tmp)

    def upload_thumb(self):
        from kivy.graphics.texture import Texture
        w, h, pixels = self.thumb
        texture = Texture.create((w, h), 'rgb', 'ubyte')
        texture.blit_buffer(pixels, colorfmt='rgb')
        self.texture = texture
        self.texture_size = texture.size

