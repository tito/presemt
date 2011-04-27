
from kivy.core.image import ImageLoader

SUPPORTED_IMG = []
for loader in ImageLoader.loaders:
    for ext in loader.extensions():
        if ext not in SUPPORTED_IMG:
            SUPPORTED_IMG.append(ext)
# OK, who has a better idea on how to do that that is still acceptable?
SUPPORTED_VID = ['avi', 'mpg', 'mpeg']

