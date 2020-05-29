from asciterm_generic import ArtSciTerm
from vispy import gloo, app, util
import os

class Null:
    pass

class ArtSciTermVispyProgram(gloo.Program):
    def get_uniforms(self):
        uniforms = []
        for variable in self.variables:
            if variable[0] == 'uniform':
                uniforms.append((variable[2], variable[1]))
        return uniforms

    def get_attributes(self):
        attributes = []
        for variable in self.variables:
            if variable.kind == 'attribute':
               attributesuniforms.append((variable[2], variable[1]))

        return attributes


class ArtSciTermVispy(app.Canvas, ArtSciTerm):
    def __init__(self, args, width, height, x=0, y=0, scale=2):
        self.factory = Null()
        setattr(self.factory, "create_program", ArtSciTermVispyProgram)
        setattr(self.factory, "ortho",  util.transforms.ortho)

        #self.gloo = gloo
        #self._app = app
        app.Canvas.__init__(self)
        ArtSciTerm.__init__(self, args)

    def run(self):
        super().show()
        self.app.run()

    def create_timer(self, interval):
        self.timer = app.Timer(interval='auto', connect=self.on_timer, start=True)

    def handle_main_vbuffer(self):
        self.program.bind(gloo.VertexBuffer(self.vbuffer))

    def handle_cursor_vbuffer(self):
        self.program1["position"] = gloo.VertexBuffer(self.cursor_position)

    def as_texture_2d(self, data):
        return gloo.Texture2D(data)

    def on_key_press(self, event):
        os.write(self.master_fd, str.encode(event.text))
        #self.update()

    def get_gl_detail(self, what):
        return what

    def adapt_vbuffer(self):
        pass

    def on_resize(self, event):
        self.width, self.height = event.size
        self._on_resize(self.width, self.height)

    def on_mouse_move(self, event):
        self.mouse = event.pos

    def on_timer(self, event):
        self.time = event.elapsed
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
        gloo.clear('black')
        self.draw(event)

    def quit(self):
        app.quit()
