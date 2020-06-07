from asciterm_generic import ArtSciTerm
from vispy import gloo, app, util


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
                attributes.append((variable[2], variable[1]))

        return attributes

    def to_gl_constant(self, txt):
        return txt

    GL_CLAMP = "clamp_to_edge"
    GL_POINTS = "points"
    GL_TRIANGLES = "triangles"


class ArtSciTermVispy(app.Canvas, ArtSciTerm):
    def __init__(self, args):
        self.factory = Null()
        setattr(self.factory, "create_program", ArtSciTermVispyProgram)
        setattr(self.factory, "ortho",  util.transforms.ortho)

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
        self.on_text(str.encode(event.text))
        if event.key == "Control":
            self.on_ctrl_key(True)

    def on_key_release(self, event):
        if event.key == "Control":
            self.on_ctrl_key(False)

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
        self.on_scroll(*event.delta)
        return

    def on_draw(self, event):
        gloo.clear('black')
        self.draw(event)

    def quit(self):
        app.quit()
