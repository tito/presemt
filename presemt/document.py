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
        self.infos.size = (100, 100)
        self._objects = []
        self._slides = []

    @staticmethod
    def register(name, cls):
        Document.available_objects[name] = cls

    def load(self, filename):
        with open(filename, 'r') as fd:
            j = json.loads(fd.read())
        self.infos.update(j['document'])
        for slide in j['slides']:
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

    def add_slide(self, pos, rotation, scale):
        slide = DocumentSlide()
        slide.pos = pos
        slide.rotation = rotation
        slide.scale = scale
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

