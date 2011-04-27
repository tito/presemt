'''
Document
========

Available objects (1.0)
-----------------------

Document:
    version - int
    time_creation - int
    time_modification - int
    size - tuple(int, int)


    Objects:

        [ common attributes of all objects ]
        pos - tuple(float, float)
        size - tuple(float, float)
        rotation - float
        scale - float

        Text:
            text - str
            bold - bool
            color - tuple(float, float, float, float)
            font_name - str
            font_size - float
            italic - bool

        Image:
            source - str

        Video:
            source - str

    Slides:
        Slide:
            pos - tuple(float, float)
            rotation - float
            scale - float
'''

__all__ = ('Document', )

import json
from time import time
from kivy.utils import QueryDict

class DocumentObject(QueryDict):
    __attrs__ = ('pos', 'size', 'rotation', 'scale', 'dtype')
    def __init__(self, **kwargs):
        super(DocumentObject, self).__init__(**kwargs)
        allowed_attrs = list(self.__class__.__attrs__) + \
                list(super(self.__class__, self).__attrs__)
        if [x for x in self.keys() if x not in allowed_attrs]:
            raise Exception('You are using non allowed attributes for your '
                            'object')

class TextObject(DocumentObject):
    __attrs__ = ('text', 'bold', 'color', 'font_name', 'font_size', 'italic')


class ImageObject(DocumentObject):
    __attrs__ = ('source', )


class VideoObject(DocumentObject):
    __attrs__ = ('source', )


class DocumentSlide(QueryDict):
    pass


class Document(object):
    available_objects = {}

    def __init__(self, **kwargs):
        self.infos = QueryDict()
        self.infos.version = 1
        self.infos.time_creation = time()
        self.infos.time_modification = time()
        self.infos.root_size = kwargs.get('size', (100, 100))
        self.infos.root_pos = kwargs.get('pos', (0, 0))
        self.infos.root_scale = kwargs.get('scale', 0.)
        self.infos.root_rotation = kwargs.get('rotation', 0.)
        self._objects = []
        self._slides = []

    @staticmethod
    def register(name, cls):
        Document.available_objects[name] = cls

    @property
    def objects(self):
        return (QueryDict(x) for x in self._objects)

    @property
    def slides(self):
        return (QueryDict(x) for x in self._slides)

    def load(self, filename):
        with open(filename, 'r') as fd:
            j = json.loads(fd.read())
        self.infos.update(j['document'])
        for slide in j['slides']:
            thumb = slide['thumb']
            if thumb is not None:
                slide['thumb'] = self.decode_thumb(thumb)
            self._slides.append(DocumentSlide(slide))
        for obj in j['objects']:
            inst = Document.available_objects[obj['dtype']](**obj)
            self._objects.append(inst)

    def save(self, filename):
        doc = QueryDict()
        doc.document = self.infos
        doc.document.time_modification = time()
        doc.objects = self._objects
        doc.slides = self._slides
        with open(filename, 'w') as fd:
            fd.write(json.dumps(doc))

    def create_text(self, **attrs):
        text = TextObject(**attrs)
        text.dtype = 'text'
        self._objects.append(text)
        return text

    def create_image(self, **attrs):
        image = ImageObject(**attrs)
        image.dtype = 'image'
        self._objects.append(image)
        return image

    def create_video(self, **attrs):
        video = VideoObject(**attrs)
        video.dtype = 'video'
        self._objects.append(video)
        return video

    def encode_thumb(self, thumb):
        import pygame
        import tempfile
        import os
        import base64

        w, h, pixels = thumb
        # convert pixels to jpeg
        surface = pygame.image.fromstring(pixels, (w, h), 'RGBA', True)
        fn = tempfile.mktemp('.jpg')
        pygame.image.save(surface, fn)
        # read jpeg
        with open(fn) as fd:
            data = fd.read()
        # delete file
        os.unlink(fn)
        # convert to base64
        data = base64.b64encode(data)
        return (w, h, 'data:image/jpeg;base64,' + data)

    def decode_thumb(self, thumb):
        header = 'data:image/jpeg;base64,'
        w, h, data = thumb
        if not data.startswith('data:image/jpeg;base64,'):
            return None
        data = data[len(header):]
        import base64
        import StringIO
        import pygame
        data = StringIO.StringIO(base64.b64decode(data))
        surface = pygame.image.load(data, 'image.jpg')
        return (w, h, pygame.image.tostring(surface, 'RGB', True))

    def add_slide(self, pos, rotation, scale, thumb):
        if thumb is not None:
            thumb = self.encode_thumb(thumb)
        slide = DocumentSlide()
        slide.pos = pos
        slide.rotation = rotation
        slide.scale = scale
        slide.thumb = thumb
        self._slides.append(slide)
        return slide

    def remove_slide(self, slide):
        self._slides.remove(slide)

    def clear_slides(self):
        self._slides = {}

# register object that can be used in document
Document.register('text', TextObject)
Document.register('image', ImageObject)
Document.register('video', VideoObject)

if __name__ == '__main__':
    doc = Document()
    doc.create_text(text='Hello world', pos=(2, 3))
    doc.save('output.json')
    doc = Document()
    doc.load('output.json')

