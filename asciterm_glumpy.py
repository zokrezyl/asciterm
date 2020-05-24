from asciterm_generic import ArtSciTerm
from glumpy import gloo, app, glm, gl
import numpy as np
import os
import time


class ArtSciTermGlumpy(ArtSciTerm):
    def __init__(self, args, width, height, x=0, y=0, scale=2):
        self.gloo = gloo
        self._app = app
        self.ortho = glm.ortho
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
        self.adapt_to_dim(width, height)

    def on_character(self, text):
        print(text)
        if self.master_fd is not None:
            os.write(self.master_fd, str.encode(text))
    
    def get_gl_detail(self, what):
        return {
                'clamp_to_edge': gl.GL_CLAMP,
                'points': gl.GL_POINTS,
                'triangles': gl.GL_TRIANGLES
                }[what]


    def adapt_vbuffer(self):
        self.vbuffer = self.vbuffer.view(self.gloo.VertexBuffer)
        self.program.bind(self.vbuffer)
        print("adapt_vbuffer")

