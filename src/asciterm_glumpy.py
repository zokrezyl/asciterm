from asciterm_generic import ArtSciTerm
from glumpy import gloo, app, glm, gl
from glumpy.ext.ffmpeg_writer import FFMPEG_VideoWriter
import numpy as np
import os
import time

from glumpy.app.movie import record


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
            'triangles': gl.GL_TRIANGLES,
            'triangle_strip': gl.GL_TRIANGLE_STRIP
            }[what]

    GL_POINTS = gl.GL_POINTS
    GL_TRIANGLES = gl.GL_TRIANGLES
    GL_TRIANGLE_STRIP = gl.GL_TRIANGLE_STRIP
    GL_CLAMP = gl.GL_CLAMP


class ArtSciTermGlumpy(ArtSciTerm):
    def __init__(self, args):
        self.factory = Null()
        setattr(self.factory, "create_program", ArtSciTermGlumpyProgram)
        setattr(self.factory, "ortho", glm.ortho)

        ArtSciTerm.__init__(self, args)

    def run(self):
        app.use("qt5")
        self.window = app.Window(width = self.width, height = self.height)
        #self.window = app.Window()
        self.window.attach(self)
        #app.clock.set_fps_limit(20)
        clock = app.__init__(backend=app.__backend__)
        if False:
            with record(self.window, "cube.mp4", fps=20):
                app.run(framerate=20)
        else:
            while True:
                #dt = clock.tick()
                #self.program1['time'] = dt*5
                time.sleep(0.01)
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

    def on_draw(self, event):
        self.window.clear()
        self.draw(event)

    def on_resize(self, width, height):
        self._on_resize(width, height)

    def on_key_press(self, key, modifiers):
        if modifiers & app.window.key.MOD_CTRL:
            self.on_ctrl_key(True)

    def on_key_release(self, key, modifiers):
        if not modifiers & app.window.key.MOD_CTRL:
            self.on_ctrl_key(False)

    def on_character(self, text):
        self.on_text(str.encode(text))

    def adapt_vbuffer(self):
        self.vbuffer = self.vbuffer.view(gloo.VertexBuffer)
        self.program.bind(self.vbuffer)

    def quit(self):
        app.quit()
        self.finish = True

    def on_mouse_scroll(self, x, y, dx, dy):
        self.on_scroll(dx, dy)
