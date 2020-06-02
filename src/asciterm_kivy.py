from asciterm_generic import ArtSciTerm
import os

from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import RenderContext


class ArtSciTermKivy(FloatLayout, ArtSciTerm):
    def __init__(self, args, width, height, x=0, y=0, scale=2):
        self.gloo = gloo
        self._app = app
        self.ortho = util.transforms.ortho
        self.program = RenderContext()
        self.program1 = RenderContext()
        raise Exception("Not yet implemented... under work")
        app.Canvas.__init__(self)
        ArtSciTerm.__init__(args, self)


    def run(self):
        super().show()
        self.app.run()

    def create_timer(self, interval):
        self.timer = app.Timer(interval=0.2, connect=self.on_timer, start=True)

    def handle_main_vbuffer(self):
        self.program.bind(self.gloo.VertexBuffer(self.vbuffer))

    def handle_cursor_vbuffer(self):
        self.program1["position"] = self.gloo.VertexBuffer(self.cursor_position)

    def as_texture_2d(self, data):
        return self.gloo.Texture2D(data)

    def on_key_press(self, event):
        os.write(self.master_fd, str.encode(event.text))
        #self.update()

    def get_gl_detail(self, what):
        return what

    def adapt_vbuffer(self):
        pass

    def on_resize(self, event):
        self.width, self.height = event.size
        self.adapt_to_dim(self.width, self.height)

    def on_timer(self, event):
        print("timer...")
        self.program1['time'] = event.elapsed*5
        self.update()

    def on_mouse_wheel(self, event):
        self.scale += event.delta[1]/10
        if self.scale < 0.5:
            self.scale = 0.5
        self.adapt_to_dim(self.width, self.height)
        self.program["scale"]= self.scale
        #self.program1["scale"]= self.scale
        #self.on_cursor_move()
        self.dirty = True

    def on_draw(self, event):
        print("on draw..")
        self.gloo.clear('black')
        self.draw(event)
