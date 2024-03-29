import pyglet
from .renderer import Renderer

PALETTE = [
    0x000000,
    0x1d2b53,
    0x7e2553,
    0x008751,
    0xab5236,
    0x5f574f,
    0xc2c3c7,
    0xfff1e8,
    0xff004d,
    0xffa300,
    0xffec27,
    0x00e436,
    0x29adff,
    0x83769c,
    0xff77a8,
    0xffccaa,
]

BANK_SIZE = (256, 256)
BANK_COUNT = 8
DRAW_COUNT = 10000


class Window(pyglet.window.Window):
    def __init__(self, app):
        super().__init__(app._width * app._scale, app._height * app._scale)

        self.app = app
        self.renderer = Renderer(app._width, app._height, BANK_SIZE,
                                 BANK_COUNT, DRAW_COUNT)

        app.bank = self.renderer.bank
        app.clip = self.renderer.clip
        app.pal = self.renderer.pal
        app.cls = self.renderer.cls
        app.pix = self.renderer.pix
        app.line = self.renderer.line
        app.rect = self.renderer.rect
        app.rectb = self.renderer.rectb
        app.circ = self.renderer.circ
        app.circb = self.renderer.circb
        app.blt = self.renderer.blt
        app.text = self.renderer.text

        pyglet.clock.schedule_interval(self.update, 1 / app._fps)

    def update(self, _):
        self.renderer.begin()
        self.app.update()
        self.renderer.end()

    def on_draw(self):
        window_width, window_height = self.get_viewport_size()
        scale_x = window_width // self.renderer.width
        scale_y = window_height // self.renderer.height
        scale = min(scale_x, scale_y)
        width = self.renderer.width * scale
        height = self.renderer.height * scale
        left = (window_width - width) // 2
        bottom = (window_height - height) // 2

        self.renderer.render(left, bottom, width, height, self.app._palette,
                             self.app._bg_color)

    def on_key_press(self, key, modifiers):
        self.app.key_press(key, modifiers)

    def on_text(self, text):
        self.app.text_input(text)


class App:
    def __init__(self,
                 width,
                 height,
                 scale,
                 *,
                 palette=PALETTE,
                 bg_color=0x000000,
                 fps=60):
        self._width = width
        self._height = height
        self._scale = scale
        self._palette = palette[:]
        self._bg_color = bg_color
        self._fps = fps
        self._window = Window(self)

    def update(self):
        pass

    def key_press(self, key, modifiers):
        pass

    def text_input(self, text):
        pass

    @staticmethod
    def run():
        pyglet.app.run()
