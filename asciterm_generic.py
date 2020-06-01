import os
import tty
import pty
import time
import fcntl
import termios
import array
import threading
import numpy as np
from OpenGL import GL as gl
import glumpy
from select import select

from vterm import VTerm, VTermScreenCallbacks_s, VTermRect_s, VTermPos_s

import queue

from esc_seq_parser import BufferProcessor
from progman import ProgramManager

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
        self.mouse = (0, 0)
        self.width, self.height = width, height
        self.cols = width  // int(self.char_width * self.scale)
        self.rows = height // int(self.char_height * self.scale)
        self.program["cols"] = self.cols
        with self.vt_lock:
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
        self.program["projection"] = self.factory.ortho(0, width, height, 0, -1, +1)

        self.progman.on_screen_size_change(self.scale, self.cols, self.rows, width, height)

        self.adapt_vbuffer()

        self.handle_main_vbuffer()

    def __init__(self, args, width, height, scale):
        self.width = width
        self.height = height
        self.scale = scale
        self.char_width = 6.0
        self.char_height = 13.0
        self.start_time = time.time()
        self.queue = queue.Queue()
        self.args = args
        self.finish = False
        self.dirty = True
        self.cursor_pos = VTermPos_s(0,0)
        self.char_data = bytes()
        self.master_fd = None

        self.vt = ArtSciVTerm(args[0].libvterm_path, 100, 100, self)
        self.vt_lock = threading.Lock()
        self.progman_lock = threading.Lock()


        self.program = self.factory.create_program(vertex, fragment)
        self.program1 = self.factory.create_program(vertex1, fragment1, count=5)
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

        self.progman = ProgramManager(self.factory, self.width,
                self.height, self.char_width, self.char_height)

        self.buffer_processor = BufferProcessor()
        self.adapt_to_dim(self.width, self.height)


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
        self.program["tex_data"].wrapping = self.program.to_gl_constant('clamp_to_edge')

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

        threading.Thread(target=self.pty_function).start()

    def _on_resize(self, width, height):
        self.adapt_to_dim(width, height)

    def on_cursor_move(self):
        x1 = 2 * self.cursor_pos.col / self.cols - 1
        y1 = 1 - 2 * (self.cursor_pos.row + 0.7)/ self.rows

        x2 = x1 - 2 * self.scale * self.char_width / self.width
        y2 = y1 - 2 * self.scale * self.char_height / self.height

        self.cursor_position = [((3*x1 + x2)/4, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1)]
        self.handle_cursor_vbuffer()



    def draw(self, event):
        time_now = time.time()
        time_elapsed = time_now - self.start_time
        gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_BLEND)

        if self.dirty:
            try:
                self.process()
            except Exception as exc:
                print("exception ... ", exc)
                return

        self.dirty = False

        self.program1['time'] = time_elapsed*5
        # TODO .. look into vispy/gloo/wrappers.py to use vispy functions
        gl.glBlendFuncSeparate(gl.GL_ONE,  gl.GL_ONE,
                            gl.GL_ZERO, gl.GL_ONE_MINUS_SRC_ALPHA)

        # self.window.clear()
        with self.progman_lock:
            mouse = (2*self.mouse[0]/self.width - 1, 1 - 2*self.mouse[1]/self.height )
            for internal_id, prog_wrap in self.progman.prog_wraps.items():
                prog_wrap.draw(time_now = time_now, mouse = mouse)

        self.program.draw(self.program.GL_POINTS)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)
        self.program1.draw(self.program1.GL_TRIANGLES)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)


    def process(self):
        """ Put text at (row,col) """

        with self.vt_lock:
            buf = np.ctypeslib.as_array(self.vt.screen.contents.buffer, (self.rows*self.cols, ))
            codes = buf["chars"][:,0:1].reshape((self.rows*self.cols))
        # 
        as_str = codes.astype('b').tostring()
        magic_pos = 0
        first_magic_pos = -1
        prev_prog_id = -1
        prog_id = -1
        prog_positions = {}
        codes = codes.copy()
        magic_rows = 1
        with self.progman_lock:
            for internal_id, prog_wrap in self.progman.prog_wraps.items():
                prog_wrap.active = False
        while True:
            magic_pos = as_str.find(BufferProcessor.magic_string, magic_pos)
            if (magic_pos != -1):
                int_pos = magic_pos + len(BufferProcessor.magic_string)
                prog_id = int(as_str[int_pos: int_pos+8].decode('ascii'))
                if first_magic_pos == -1:
                    first_magic_pos = magic_pos
                if prog_id == prev_prog_id:
                    magic_rows += 1

            if magic_pos == -1 and prog_id == -1:
                break

            if magic_pos == -1 or (prog_id != prev_prog_id and prev_prog_id != -1):
                codes[first_magic_pos: first_magic_pos + self.cols * magic_rows] = 0
                with self.progman_lock:
                    to_update_prog_id = prog_id if magic_pos == -1 else prev_prog_id
                    self.progman.set_prog_last_row(to_update_prog_id, first_magic_pos / self.cols + magic_rows)
                first_magic_pos = magic_pos;
                if magic_pos == -1:
                    break
                magic_rows = 1

            magic_pos += 1
            prev_prog_id = prog_id

        self.vbuffer["pindex"] = np.arange(self.rows*self.cols)
        self.vbuffer["gindex"] = 2  # index of space in our font
        self.vbuffer["gindex"][:len(codes)] = np.searchsorted(self._codes, codes)

        self.vbuffer['fg'] = buf['fg']/255
        self.vbuffer['bg'] = buf['bg']/255
        self.handle_main_vbuffer()


    def pty_function(self):
        pid, self.master_fd = pty.fork()
        if pid == 0:  # CHILD
            if len(self.args[1]) > 0:
                argv = self.args[1]
            else:
                shell = os.environ.get('SHELL', 'sh')
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
        max_size = 10*1024*1024
        char_data = bytes()
        while True:
            rfds, _, _ = select(fds, [], [])
            try:
                os.waitpid(pid, os.WNOHANG)
            except Exception as exc:
                # todo log 
                self.quit()
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
                        try:
                            (cmds, buf) = self.buffer_processor.process(char_data)
                        except:
                            self.last_time = time_now
                            continue
                        with self.vt_lock:
                            self.vt.push(buf)
                        with self.progman_lock:
                            for cmd in cmds:
                                self.progman.process_cmd(cmd)
                        char_data = bytes()
                        self.dirty = True
                        self.update()
                    if data is None:
                        break

