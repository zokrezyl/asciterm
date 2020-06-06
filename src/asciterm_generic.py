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
from select import select

from vterm import VTerm, VTermScreenCallbacks_s, VTermRect_s, VTermPos_s, VTermScreenCell_s

import queue

from esc_seq_parser import BufferProcessor
from progman import ProgramManager
from font import ArtSciTermFont


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


from ctypes import create_string_buffer, sizeof, memmove
class ArtSciVTerm(VTerm):
    def __init__(self, progman, libvterm_path, rows, cols, parent):
        self.progman = progman
        self.lock = threading.Lock()
        self.cmd_lock = threading.Lock()
        self.sb = []
        self.parent = parent
        self.codes = None
        self.cmds = []
        super().__init__(libvterm_path, rows, cols)

    def on_movecursor(self, pos, oldpos, visible, user):
        self.parent.cursor_pos = pos
        self.parent.cursor_oldpos = oldpos
        self.parent.on_cursor_move()
        return True

    def process_cmd_queue(self):
        cmds = None
        with self.cmd_lock:
            cmds = self.cmds
            self.cmds = []
        for cmd in cmds:
            print(cmd)
            self.progman.process_cmd(cmd)

    def on_damage(self, rect, user):
        #print("on_damage")
        buf = np.ctypeslib.as_array(self.screen.contents.buffer, (self.rows*self.cols, ))
        self.codes = buf["chars"][:, 0:1].reshape((self.rows*self.cols))
        self.process_cmd_queue()
        return True

    def on_moverect(self, dest, src, user):
        buf = np.ctypeslib.as_array(self.screen.contents.buffer, (self.rows*self.cols, ))
        self.codes = buf["chars"][:, 0:1].reshape((self.rows*self.cols))
        #print("moverect")
        self.process_cmd_queue()
        return True
        return True

    def on_set_term_title(self, title):
        self.parent.title = title.decode('ascii')
        return True

    def on_set_term_altscreen(self, screen):
        self.parent.altscreen = screen
        return True

    def resize(self, rows, cols):
        with self.lock:
            super().resize(rows, cols)

    def on_sb_pushline(self, cols, cells, user):
        #print("pushline ", cols)
        #print("pushline ", [getattr(cells[0], attr[0]) for attr in cells[0]._fields_])
        buf = create_string_buffer(cols * sizeof(VTermScreenCell_s))
        memmove(buf, cells, cols * sizeof(cells.contents))
        self.sb.append((cols, buf))
        #restore it from some internal buffer
        return True

    def on_sb_popline(self, cols, cells, user):
        #print("popline ", cols, sizeof(VTermScreenCell_s))
        if len(self.sb) > 0:
        #TODO restore it from the internal buffer
            our_cols, buf = self.sb.pop(0)
            #print("we have to do ", our_cols, cols, sizeof(VTermScreenCell_s))
            min_cols = min(cols, our_cols)
            memmove(cells, buf, min_cols * sizeof(VTermScreenCell_s))
            for col in range(min_cols, cols):
                cells[col].width = 1
            #print("popline ", [getattr(cells[0], attr[0]) for attr in cells[0]._fields_])
            #print("done??")
            return True
        else:
            #print("popline nothing to do...")
            return False


class ArtSciTerm:

    def adapt_to_dim(self, width, height):
        self.mouse = (0, 0)
        self.width, self.height = width, height
        self.cols = width // int(self.font.char_width * self.scale)
        self.rows = height // int(self.font.char_height * self.scale)
        self.program["cols"] = self.cols
        self.vt.resize(self.rows, self.cols)
        if self.master_fd:
            buf = array.array('h', [self.rows, self.cols, 0, 0])
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, buf)

        self.vbuffer = np.zeros(self.rows*self.cols, [("pindex", np.float32, 1),
                                             ("gindex", np.float32, 1),
                                             ("fg", np.float32, 4),
                                             ("bg", np.float32, 4)])
        self.program["projection"] = self.factory.ortho(0, width, height, 0, -1, +1)

        self.vt.progman.on_screen_size_change(self.scale, self.cols, self.rows, width, height)

        self.adapt_vbuffer()

        self.handle_main_vbuffer()

    def __init__(self, args):

        self.src_path = os.path.dirname(os.path.abspath(__file__))

        self.altscreen = False
        self.width = 1000
        self.height = 1000
        size = args[0].size.split("x")
        if len(size) == 2:
            self.width = int(size[0])
            self.height = int(size[1])
        else:
            print("arg szie has to be in form <width>x<height>, instead got {args[0].size}, using defaults {self.width}, {self.height}")

        self.scale = float(args[0].scale)
        self.start_time = time.time()
        self.queue = queue.Queue()
        self.args = args
        self.finish = False
        self.dirty = True
        self.cursor_pos = VTermPos_s(0, 0)
        self.char_data = bytes()
        self.master_fd = None


        self.program = self.factory.create_program(
                open(os.path.join(self.src_path, "gl/term.vert.glsl")).read(),
                open(os.path.join(self.src_path, "gl/term.frag.glsl")).read())

        self.program1 = self.factory.create_program(
                open(os.path.join(self.src_path, "gl/cur.vert.glsl")).read(),
                open(os.path.join(self.src_path, "gl/cur.frag.glsl")).read(),
                count=5)

        self.program1["scale"] = self.scale

        self.font = ArtSciTermFont(self.src_path)

        progman = ProgramManager(self.factory, self.width,
                                      self.height, self.font.char_width,
                                      self.font.char_height)

        self.vt = ArtSciVTerm(progman, args[0].libvterm_path, 100, 100, self)

        self.buffer_processor = BufferProcessor()
        self.adapt_to_dim(self.width, self.height)

        self.program["tex_data"] = self.as_texture_2d(self.font.data)  # self.gloo.Texture2D(data)
        self.program["tex_data"].interpolation = gl.GL_NEAREST
        self.program["tex_data"].wrapping = self.program.to_gl_constant('clamp_to_edge')

        self.program["tex_size"] = self.font.t_width, self.font.t_height
        self.program["char_width"] = self.font.char_width
        self.program["char_height"] = self.font.char_height
        self.program["cols"] = self.cols
        self.program["scale"] = self.scale

        gl.glEnable(gl.GL_BLEND)
        self.create_timer(interval=0.01)

        gl.glEnable(gl.GL_VERTEX_PROGRAM_POINT_SIZE)
        gl.glEnable(gl.GL_POINT_SPRITE)

        threading.Thread(target=self.pty_function).start()

    def _on_resize(self, width, height):
        self.adapt_to_dim(width, height)

    def on_cursor_move(self):
        x1 = 2 * self.cursor_pos.col / self.cols - 1
        y1 = 1 - 2 * (self.cursor_pos.row + 0.7) / self.rows

        x2 = x1 - 2 * self.scale * self.font.char_width / self.width
        y2 = y1 - 2 * self.scale * self.font.char_height / self.height

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
        gl.glBlendFuncSeparate(gl.GL_ONE,  gl.GL_ONE,
                               gl.GL_ZERO, gl.GL_ONE_MINUS_SRC_ALPHA)

        if not self.altscreen:
            for internal_id, prog_wrap in self.vt.progman.prog_wraps.items():
                prog_wrap.draw(time_now=time_now, mouse=self.mouse)

        self.program.draw(self.program.GL_POINTS)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)
        self.program1.draw(self.program1.GL_TRIANGLES)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE_MINUS_SRC_ALPHA, gl.GL_SRC_ALPHA)

    def process(self):
        """ Put text at (row,col) """
        if self.vt.codes is None:
            print("no codes")
            return

        with self.vt.lock:
            buf = np.ctypeslib.as_array(self.vt.screen.contents.buffer, (self.rows*self.cols, ))
            codes = buf["chars"][:, 0:1].reshape((self.rows*self.cols))
            codes = self.vt.codes

        as_str = codes.astype('b').tostring()
        magic_pos = 0
        first_magic_pos = -1
        prev_prog_id = -1
        prog_id = -1
        codes = codes.copy()
        magic_rows = 1
        for internal_id, prog_wrap in self.vt.progman.prog_wraps.items():
            prog_wrap.active = False
        while not self.altscreen:
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
                to_update_prog_id = prog_id if magic_pos == -1 else prev_prog_id
                self.vt.progman.set_prog_last_row(to_update_prog_id, first_magic_pos / self.cols + magic_rows)
                first_magic_pos = magic_pos;
                if magic_pos == -1:
                    break
                magic_rows = 1

            magic_pos += 1
            prev_prog_id = prog_id

        self.vbuffer["pindex"] = np.arange(self.rows*self.cols)
        self.vbuffer["gindex"] = 2  # index of space in our font
        self.vbuffer["gindex"][:len(codes)] = np.searchsorted(self.font._codes, codes)

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
            except Exception:
                self.quit()
                return
            if self.master_fd in rfds:
                while True:
                    time_now = time.time()
                    try:
                        data = os.read(self.master_fd, max_size)
                    except Exception:
                        data = None
                    if data is not None:
                        char_data += data

                    if time_now - self.last_time > 0.2 \
                            or data is None \
                            or len(char_data) > max_size:
                        try:
                            (cmds, buf) = self.buffer_processor.process(char_data)
                        except Exception:
                            self.last_time = time_now
                            continue
                        with self.vt.cmd_lock:
                            self.vt.cmds.extend(cmds)
                        with self.vt.lock:
                            self.vt.push(buf)
                        char_data = bytes()
                        self.dirty = True
                        self.update()
                    if data is None:
                        break

