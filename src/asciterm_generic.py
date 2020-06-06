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
from font import ArtSciTermFont


class ArtSciVTerm(VTerm):
    def __init__(self, libvterm_path, rows, cols, parent):
        self.parent = parent
        super().__init__(libvterm_path, rows, cols)

    def on_movecursor(self, pos, oldpos, visible, user):
        self.parent.cursor_pos = pos
        self.parent.cursor_oldpos = oldpos
        self.parent.on_cursor_move()
        return True

    def on_damage(self, rect, user):
        return True

    def on_set_term_title(self, title):
        self.parent.title = title.decode('ascii')
        return True

    def on_set_term_altscreen(self, screen):
        self.parent.altscreen = screen
        return True


class ArtSciTerm:

    def adapt_to_dim(self, width, height):
        self.mouse = (0, 0)
        self.width, self.height = width, height
        self.cols = width // int(self.font.char_width * self.scale)
        self.rows = height // int(self.font.char_height * self.scale)
        self.program["cols"] = self.cols
        with self.vt_lock:
            self.vt.resize(self.rows, self.cols)
        if self.master_fd:
            buf = array.array('h', [self.rows, self.cols, 0, 0])
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, buf)

        self.vbuffer = np.zeros(self.rows*self.cols, [("pindex", np.float32, 1),
                                             ("gindex", np.float32, 1),
                                             ("fg", np.float32, 4),
                                             ("bg", np.float32, 4)])
        self.program["projection"] = self.factory.ortho(0, width, height, 0, -1, +1)

        self.progman.on_screen_size_change(self.scale, self.cols, self.rows, width, height)

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

        self.vt = ArtSciVTerm(args[0].libvterm_path, 100, 100, self)
        self.vt_lock = threading.Lock()
        self.progman_lock = threading.Lock()

        self.program = self.factory.create_program(
                open(os.path.join(self.src_path, "gl/term.vert.glsl")).read(),
                open(os.path.join(self.src_path, "gl/term.frag.glsl")).read())

        self.program1 = self.factory.create_program(
                open(os.path.join(self.src_path, "gl/cur.vert.glsl")).read(),
                open(os.path.join(self.src_path, "gl/cur.frag.glsl")).read(),
                count=5)

        self.program1["scale"] = self.scale

        self.font = ArtSciTermFont(self.src_path)

        self.progman = ProgramManager(self.factory, self.width,
                                      self.height, self.font.char_width,
                                      self.font.char_height)

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
        # TODO .. look into vispy/gloo/wrappers.py to use vispy functions
        gl.glBlendFuncSeparate(gl.GL_ONE,  gl.GL_ONE,
                               gl.GL_ZERO, gl.GL_ONE_MINUS_SRC_ALPHA)

        # self.window.clear()
        with self.progman_lock:
            if not self.altscreen:
                for internal_id, prog_wrap in self.progman.prog_wraps.items():
                    prog_wrap.draw(time_now=time_now, mouse=self.mouse)

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
            codes = buf["chars"][:, 0:1].reshape((self.rows*self.cols))

        as_str = codes.astype('b').tostring()
        magic_pos = 0
        first_magic_pos = -1
        prev_prog_id = -1
        prog_id = -1
        codes = codes.copy()
        magic_rows = 1
        with self.progman_lock:
            for internal_id, prog_wrap in self.progman.prog_wraps.items():
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

