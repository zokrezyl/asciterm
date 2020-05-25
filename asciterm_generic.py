import os
import tty
import pty
import time
import fcntl
import termios
import array
import msgpack
import base64
import threading
import numpy as np
from OpenGL import GL as gl
import glumpy
from select import select

from vterm import VTerm, VTermScreenCallbacks_s, VTermRect_s, VTermPos_s

import queue

from esc_seq_parser import BufferProcessor

vertex = """
#version 120

// Uniforms
// --------
uniform sampler2D tex_data;
uniform vec2 tex_size;
uniform float char_width;
uniform float char_height;
//uniform float rows;
uniform float cols;
uniform float scale;
//uniform vec4 foreground;
//uniform vec4 background;
//uniform vec2 selection;
uniform mat4 projection;

// Attributes
// ----------
attribute float pindex;
attribute float gindex;
attribute vec4 fg;
attribute vec4 bg;


// Varyings
// --------
varying vec4 v_fg;
varying vec4 v_bg;
varying vec2 v_texcoord;
varying vec4 v_foreground;
varying vec4 v_background;


// Main
// ----
void main (void)
{
    // Compute char position from pindex
    float x = mod(pindex, cols);
    float y = floor(pindex/cols);
    vec2 P = (vec2(x,y) * vec2(char_width, char_height)) * scale;
    P += vec2(char_height, char_height)*scale/2.0;
    P += vec2(2.0, 2.0);
    gl_Position = projection*vec4(P, 0.0, 1.0);
    gl_PointSize = char_height * scale ;

    v_fg = fg.yzwx;
    v_bg = bg.yzwx;

    float n = tex_size.x/char_width;
    x = 0.5 +  mod(gindex, n) * char_width;
    y = 0.5 + floor(gindex/n) * char_height;
    v_texcoord = vec2(x/tex_size.x, y/tex_size.y);
}
"""

fragment = """
#version 120

// Uniforms
// --------
uniform sampler2D tex_data;
uniform vec2 tex_size;
uniform float char_width;
uniform float char_height;
//uniform float rows;
uniform float cols;
uniform float scale;
//uniform vec2 selection;
//uniform vec4 foreground;


// Varyings
// --------
varying vec2 v_texcoord;
//varying vec4 v_background;
//varying vec4 v_foreground;
varying vec4 v_fg;
varying vec4 v_bg;


// Main
// ----
void main(void)
{
    vec2 uv = floor(gl_PointCoord.xy * char_height);
    if(uv.x > (char_width-1.0)) discard;
    if(uv.y > (char_height-1.0)) discard;
    float v = texture2D(tex_data, v_texcoord+uv/tex_size).r;
    gl_FragColor = v * v_fg + (1.0-v) * v_bg;
}
"""

vertex1 = """
#version 120
    uniform float scale;
    attribute vec2 position;
    void main()
    {
        //gl_Position = vec4(position, 0.0, 1)*scale;
        gl_Position = vec4(position, 0.0, 1);
    } """

fragment1 = """
#version 120
    uniform vec4 color;
    uniform float time;
    void main()
    {
        gl_FragColor = vec4(1.0*sin(time), 0.7*cos(2*time), 0.7, 0.2);
    } """

vertex2 = """
#version 120
    attribute vec2 position;
    attribute vec2 texcoord;

    varying vec2 v_texcoord;
    void main()
    {
        gl_Position = vec4(position, 0.0, 1.0);
        v_texcoord = vec2(texcoord.y, texcoord.x);
    } """

fragment2 = """
#version 120
    uniform sampler2D texture;
    varying vec2 v_texcoord;
    void main()
    {
        //gl_FragColor.rgb = texture2D(tex_data, gl_FragCoord);
        //gl_FragColor = vec4(1.0, 1.0, 1.0, 0.5);
        gl_FragColor.xy = texture2D(texture, v_texcoord).yx;
        gl_FragColor.a = 0.5;
    } """


class ArtSciVTerm(VTerm):
    def __init__(self, libvterm_path, rows, cols, parent):
        self.parent = parent
        super().__init__(libvterm_path, rows, cols)

    def on_movecursor(self, pos, oldpos, visible, user):
        self.parent.cursor_pos = pos
        self.parent.cursor_oldpos = oldpos
        self.parent.on_cursor_move()
        return int(True)

    def on_damage(self, rect, user):
        return int(True)


class ArtSciTerm:

    def adapt_to_dim(self, width, height):
        self.width = width
        self.height = height
        self.cols = width  // int(self.char_width * self.scale)
        self.rows = height // int(self.char_height * self.scale)
        self.program["cols"] = self.cols

        self.vt.resize(self.rows, self.cols)
        if self.master_fd:
            buf = array.array('h', [self.rows, self.cols, 0, 0])
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, buf)
        else:
            pass # nothing bad.. we are initializing

        self.vbuffer = np.zeros(self.rows*self.cols, [("pindex", np.float32, 1),
                                             ("gindex", np.float32, 1),
                                             ("fg", np.float32, 4),
                                             ("bg", np.float32, 4)])
        self.program["projection"] = self.ortho(0, width, height, 0, -1, +1)
        self.adapt_vbuffer()

        self.handle_main_vbuffer()

    def __init__(self, args):
        self.programs = []
        self.queue = queue.Queue()
        self.args = args
        self.finish = False
        self.scale = 2
        self.dirty = True
        self.cursor_pos = VTermPos_s(0,0)
        self.mouse_wheel = 0
        self.char_data = bytes()
        self.master_fd = None

        self.vt = ArtSciVTerm(args[0].libvterm_path, 100, 100, self)

        self.scale = 2
        self.char_width = 6.0
        self.char_height = 13.0

        self.program = self.gloo.Program(vertex, fragment)
        self.program1 = self.gloo.Program(vertex1, fragment1, count=6)
        self.program1["scale"]= self.scale

        # self.program2 = self.gloo.Program(vertex2, fragment2, count=4)
        # self.program2['position'] = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        # self.program2['texcoord'] = [(0, 0), (1, 0), (0, 1), (1, 1)]

        # Build a font array that holds regular, italic & bold font
        # Regular:      0 to   65536-1
        # Italic :  65536 to 2*65536-1
        # Bold :  2*65536 to 3*65536-1
        regular = glumpy.data.get("6x13-regular.npy")
        italic = glumpy.data.get("6x13-italic.npy")
        bold  = glumpy.data.get("6x13-bold.npy")
        n1 = len(regular)
        n2 = len(italic)
        n3 = len(bold)
        n = n1+n2+n3
        dtype = [ ("code", np.uint32, 1),
                  ("data", np.uint8, 10)]
        font = np.zeros(n, dtype)
        font[:n1] = regular
        font[n1:n1+n2] = italic
        font[n1:n1+n2]["code"] += 1*65536
        font[n1+n2:n1+n2+n3] = bold
        font[n1+n2:n1+n2+n3]["code"] += 2*65536
        font["data"][0] = font["data"][1] #we set the character of space for zero

        self.adapt_to_dim(300, 300)

        # Build a texture out of glyph arrays (need to unpack bits)
        # This code is specific for a character size of 6x13
        n = len(font)
        G = np.unpackbits(font["data"].ravel())
        G = G.reshape(n,80)[:,:78].reshape(n,13,6)

        self.t_width, self.t_height = 6*128, 13*((n//128)+1)
        data = np.zeros((self.t_height, self.t_width), np.ubyte)

        for i in range(n):
            r = 13*(i//128)
            c = 6*(i % 128)
            data[r:r+13,c:c+6] = G[i]*255

        # Store char codes
        self._codes = font["code"]
        # Fill program uniforms
        self.data = data
        self.program["tex_data"] = self.as_texture_2d(data) # self.gloo.Texture2D(data)
        self.program["tex_data"].interpolation = gl.GL_NEAREST
        self.program["tex_data"].wrapping = self.get_gl_detail('clamp_to_edge')

        # self.program2["texture"] = self.as_texture_2d(data) #self.gloo.Texture2D(data)
        # self.program2["texture"].interpolation = gl.GL_NEAREST
        # self.program2["texture"].wrapping = 'clamp_to_edge'

        self.program["tex_size"] = self.t_width, self.t_height
        self.program["char_width"] = self.char_width
        self.program["char_height"]= self.char_height
        self.program["cols"] = self.cols
        self.program["scale"]= self.scale

        gl.glEnable(gl.GL_BLEND)
        self.create_timer(interval=0.01)

        gl.glEnable(gl.GL_VERTEX_PROGRAM_POINT_SIZE)
        gl.glEnable(gl.GL_POINT_SPRITE)

        threading.Thread(target=self.pty_function, args=(self,)).start()

    def on_cursor_move(self):
        x1 = self.cursor_pos.col * self.char_width * 1.0
        y1 = (self.rows - self.cursor_pos.row) * self.char_height * 1.0 - self.char_height/4.0

        x2 = (self.cursor_pos.col + 1)* self.char_width
        y2 = (self.rows - self.cursor_pos.row - 1)* self.char_height * 1.0 - self.char_height/4.0

        x1 = 2*x1*self.scale/self.width - 1
        x2 = 2*x2*self.scale/self.width - 1
        y1 = 2*y1*self.scale/self.height - 1
        y2 = 2*y2*self.scale/self.height - 1

        self.cursor_position = [((3*x1 + x2)/4, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)]
        self.handle_cursor_vbuffer()


    def process_program(self, program):
        vertex_shader = None
        fragment_shader = None
        attributes = {}
        uniforms = {}
        if "vertex_shader" in program:
            vertex_shader = base64.b64decode(program["vertex_shader"].encode('ascii')).decode('ascii')
        if "fragment_shader" in program:
            fragment_shader = base64.b64decode(program["fragment_shader"].encode('ascii')).decode('ascii')
        if "uniforms" in program:
            uniforms = msgpack.unpackb(base64.b64decode(program["uniforms"].encode('ascii')))
        if "attributes" in program:
            attributes = msgpack.unpackb(base64.b64decode(program["attributes"].encode('ascii')))

        program = self.gloo.Program(vertex_shader, fragment_shader)

        for key, value in attributes.items():
            program[key.decode('ascii')] = value

        for key, value in uniforms.items():
            program[key.decode('ascii')] = value

        self.programs.append(program)

    def draw(self, event):
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_BLEND)

        if self.dirty:
            self.process()
        self.dirty = False

        #TODO .. look into vispy/gloo/wrappers.py to use vispy functions
        gl.glBlendFuncSeparate(gl.GL_ONE,  gl.GL_ONE,
                            gl.GL_ZERO, gl.GL_ONE_MINUS_SRC_ALPHA)

        #self.window.clear()
        for program in self.programs:
            program.draw()

        self.program.draw(self.get_gl_detail('points'))

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)
        self.program1.draw(self.get_gl_detail('triangles'))

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)


    def process(self):
        """ Put text at (row,col) """

        buf = np.ctypeslib.as_array(self.vt.screen.contents.buffer, (self.rows*self.cols, ))
        codes = buf["chars"][:,0:1].reshape((self.rows*self.cols))

        self.vbuffer["pindex"] = np.arange(self.rows*self.cols)
        self.vbuffer["gindex"] = 2  # index of space in our font
        self.vbuffer["gindex"][:len(codes)] = np.searchsorted(self._codes, codes)

        self.vbuffer['fg'] = buf['fg']/255
        self.vbuffer['bg'] = buf['bg']/255
        self.handle_main_vbuffer()

    def pty_function(self, terminal):
        shell = os.environ.get('SHELL', 'sh')
        pid, self.master_fd = pty.fork()
        if pid == 0:  # CHILD
            argv = (shell,)
            os.execl(argv[0], *argv)
        try:
            pass
            # mode = tty.tcgetattr(0)
            # tty.setraw(0)
        except tty.error:
            pass

        os.set_blocking(self.master_fd, False)

        buf = array.array('h', [self.rows, self.cols, 0, 0])
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, buf)

        fds = [self.master_fd]
        self.last_time = time.time()
        max_size = 1024*1024
        char_data = bytes()
        while True:
            rfds, _, _ = select(fds, [], [])
            try:
                os.waitpid(pid, os.WNOHANG)
            except Exception as exc:
                # todo log 
                self._app.quit()
                self.finish = True
                return
            # rfds = [master_fd]
            if self.master_fd in rfds:
                while True:
                    time_now = time.time()
                    try:
                        data = os.read(self.master_fd, max_size)
                    except:
                        data = None
                    if data is not None:
                        char_data += data

                    if time_now - self.last_time > 0.2 or data is None or len(char_data) > max_size:
                        (programs, buf) = BufferProcessor(char_data).process()
                        self.vt.push(buf)
                        for program in programs:
                            self.process_program(program)
                        char_data = bytes()
                        self.dirty = True
                        terminal.update()
                        self.last_time = time_now
                    if data is None:
                        break

