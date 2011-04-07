from kivy.uix.floatlayout import FloatLayout

class Screen(FloatLayout):
    def __init__(self, **kwargs):
        self.app = kwargs.get('app')
        super(Screen, self).__init__(**kwargs)
