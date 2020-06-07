import time
import base64
import base64
import msgpack
import numpy as np
import re
import sys
import threading

from string import Template

VERTEX_SHADER_VARIABLES = """
uniform float time;
uniform vec4 normViewport;
"""

VERTEX_SHADER_EPILOG = """
    gl_Position = vec4(
        normViewport.x + (1 + gl_Position.x) * (normViewport.z/2.0),
        normViewport.y + (1 + gl_Position.y) * (normViewport.w/2.0),
        0.0, 1.0);
"""

FRAGMENT_SHADER_VARIABLES = """
uniform float time;
uniform vec4 viewport;
uniform vec2 mousePos;
uniform vec2 screenMousePos;
uniform vec2 screenResolution;
"""

FRAGMENT_SHADER_PROLOG = """
    vec4 relFragCoord = gl_FragCoord - vec4(viewport.xy, 0, 0)
"""

def adapt_vertex_shader(vertex_shader):

    vertex_shader = Template(vertex_shader).substitute(
        vertex_shader_variables = VERTEX_SHADER_VARIABLES,
        vertex_shader_epilog = VERTEX_SHADER_EPILOG)
    
    return vertex_shader

def adapt_fragment_shader(fragment_shader):

    fragment_shader = Template(fragment_shader).substitute(
            fragment_shader_variables = FRAGMENT_SHADER_VARIABLES,
            fragment_shader_prolog = FRAGMENT_SHADER_PROLOG)
    return fragment_shader

class ProgWrap:
    def __init__(self, factory, cmd, progman):
        self.viewport = (0, 0, 0, 0)
        self.progman = progman
        self.is_sane = False

        self.last_row = 0
        vertex_shader = None
        fragment_shader = None
        attributes = {}
        uniforms = {}

        self.title = cmd.get("title", "untitled")

        if "vertex_shader" in cmd:
            vertex_shader = adapt_vertex_shader(
                    base64.b64decode(cmd["vertex_shader"].encode('ascii')).decode('ascii'))
        if "fragment_shader" in cmd:
            fragment_shader = adapt_fragment_shader(
                    base64.b64decode(cmd["fragment_shader"].encode('ascii')).decode('ascii'))
        if "uniforms" in cmd:
            uniforms = msgpack.unpackb(base64.b64decode(cmd["uniforms"].encode('ascii')))
        if "attributes" in cmd:
            attributes = msgpack.unpackb(base64.b64decode(cmd["attributes"].encode('ascii')))

        self.draw_mode = cmd.get("draw_mode", "triangle_strip")
        self.start_col = cmd.get("start_col", 0)
        self.rows = cmd.get("rows", 0)
        self.cols = cmd.get("cols", 0)

        try:
            self.program = factory.create_program(vertex_shader, fragment_shader)
            self.is_active = False
        except Exception as exc:
            print("exception while creating program: ", exc)
            return

        for key, value in attributes.items():
            try:
                key = key.decode('ascii')
                self.program[key] = value
            except IndexError as exc:
                print(f"IndexError, could not set attribute {key}: ", exc)
            except ValueError as exc:
                print(f"ValueError, could not set attribute {key}: ", exc)

        for key, value in uniforms.items():
            try:
                key = key.decode('ascii')
                self.program[key] = value
            except IndexError as exc:
                print(f"could not uniform {key}")


        self.start_time = time.time()

        self.program["time"] = 0
        self.program["screenMousePos"] = (0, 0)
        self.program['mousePos'] = (0, 0)
        self.program["normViewport"] = (0, 0, 0, 0)

        self.first_row = 0

        self.is_sane = True

    def update_viewport(self):
        norm_view_width = 2 * self.cols / self.progman.screen_cols
        norm_view_height = 2 * self.rows / self.progman.screen_rows
        self.norm_viewport = (
                -1 + 2 * self.start_col / self.progman.screen_cols,
                1 - 2.0 * (self.last_row - 1)/self.progman.screen_rows,
                norm_view_width,
                norm_view_height)
        self.program["normViewport"] = self.norm_viewport

        view_width = self.progman.scale * self.cols * self.progman.char_width
        view_height = self.progman.scale * self.rows * self.progman.char_height

        self.viewport = (
                self.progman.scale * self.start_col * self.progman.char_width,
                self.progman.scale * (self.progman.screen_rows - self.last_row + 1) * self.progman.char_height,
                view_width,
                view_height)

        self.program["viewport"] = self.viewport
        self.program["screenResolution"] = (self.progman.screen_width, self.progman.screen_height)

    def draw(self, time_now, mouse):
        mouse = (mouse[0], self.progman.screen_height - mouse[1])
        try:
            #TODO .. refactor this.. don't update what does not change
            self.program["viewport"] = self.viewport
            self.program["screenResolution"] = (self.progman.screen_width, self.progman.screen_height)
            self.program["time"] = time_now - self.start_time
            self.program["screenMousePos"] = mouse
            self.program['mousePos'] = (mouse[0] - self.viewport[0], mouse[1] - self.viewport[1])
            self.program.draw(self.program.to_gl_constant(self.draw_mode))
        except RuntimeError as exc:
            print("Program: cannot draw...: ", exc)



class ProgramManager:
    def __init__(self, factory, char_width, char_height):
        self.lock = threading.Lock()
        self.factory = factory
        self.scale = 0
        self.screen_rows = 0
        self.screen_cols = 0
        self.screen_width = 0
        self.screen_height = 0
        self.char_width = char_width
        self.char_height = char_height
        self.prog_wraps = {}

    def process_cmd(self, cmd):
        print("process cmd")
        prog_wrap = ProgWrap(self.factory, cmd, self)
        if prog_wrap.is_sane:
            self.prog_wraps[cmd["internal_id"]] = prog_wrap


    def on_screen_size_change(self, scale, cols, rows, width, height):
        self.scale = scale
        self.screen_cols = cols
        self.screen_rows = rows
        self.screen_width = width
        self.screen_height = height
        for key, program in self.prog_wraps.items():
            program.update_viewport()

    def set_prog_last_row(self, internal_id, row):
        print("last row ", row)
        program = self.prog_wraps[internal_id]
        program.last_row = row
        program.update_viewport()
        program.is_active = True

    def reset(self):
        for internal_id, prog_wrap in self.prog_wraps.items():
            prog_wrap.is_active = False

    def draw(self, mouse):
        time_now = time.time()
        for internal_id, prog_wrap in self.prog_wraps.items():
            if prog_wrap.is_active:
                prog_wrap.draw(time_now=time_now, mouse=mouse)

