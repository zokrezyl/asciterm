from asciterm_generic import ArtSciTerm
from glumpy import gloo, app, glm, gl
import numpy as np
import os
import time


class Null:
    pass

class ArtSciTermGlumpyProgram(gloo.Program):
    def get_uniforms(self):
        return self.all_uniforms

    def get_attributes(self):
        return self.all_attributes

    def to_gl_constant(self, what):
        return {
            'clamp_to_edge': gl.GL_CLAMP,
            'points': gl.GL_POINTS,
            'triangles': gl.GL_TRIANGLES
            }[what]

    GL_POINTS = gl.GL_POINTS
    GL_TRIANGLES = gl.GL_TRIANGLES
    GL_CLAMP = gl.GL_CLAMP


class ArtSciTermGlumpy(ArtSciTerm):
    def __init__(self, args, width, height, x=0, y=0, scale=2):

        self.factory = Null()
        setattr(self.factory, "create_program", ArtSciTermGlumpyProgram)
        setattr(self.factory, "ortho", glm.ortho)

        #self.gloo = gloo
        #self._app = app
        ArtSciTerm.__init__(self, args)

    def run(self):
        app.use("qt5")
        self.window = app.Window(width = self.width, height = self.height)
        self.window.attach(self)
        #app.clock.set_fps_limit(20)
        #app.run()
        clock = app.__init__(backend=app.__backend__)
        while True:
            #dt = clock.tick()
            #self.program1['time'] = dt*5
            time.sleep(0.05)
            app.__backend__.process(0.05)
            if self.finish:
                return


    def create_timer(self, interval):
        pass

    def handle_main_vbuffer(self):
        pass

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse = (x, y)

    def handle_cursor_vbuffer(self):
        self.program1['position'] = self.cursor_position

    def as_texture_2d(self, data):
        return data.view(gloo.Texture2D)
    
    def update(self):
        pass
        #self.on_draw()

    def on_draw(self, event):
        self.window.clear()
        self.draw(event)

    def on_resize(self, width, height):
        self._on_resize(width, height)

    def on_character(self, text):
        if self.master_fd is not None:
            os.write(self.master_fd, str.encode(text))
    
    def adapt_vbuffer(self):
        self.vbuffer = self.vbuffer.view(gloo.VertexBuffer)
        self.program.bind(self.vbuffer)
    
    def quit(self):
        print("quitting")
        app.quit()
        self.finish = True

