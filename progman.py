import time
import base64
import base64
import msgpack
import numpy as np

def adapt_vertex_shader(vertex_shader):
    """ we are injecting the viewport adapter
        we are not going to parse the entire grammar, we just search for the closing curly bracket

    """
    vertex_shader = "uniform vec4 viewport;\n" + vertex_shader
    curly_c_pos = vertex_shader.rfind("}")
    vertex_shader = vertex_shader[:vertex_shader.rfind("}")] + """
gl_Position = vec4(
    viewport.x + (1 + gl_Position.x) * (viewport.z/2.0),
    viewport.y + (1 + gl_Position.y) * (viewport.w/2.0),
    0.0, 1.0);
}

        """
    return vertex_shader

class ProgWrap:
    def __init__(self, factory, cmd, progman):
        self.progman = progman
        self.is_sane = False

        self.last_row = 0
        vertex_shader = None
        fragment_shader = None
        attributes = {}
        uniforms = {}

        if "name" in cmd:
            name = cmd["name"]

        if "id" in cmd:
            prog_id = cmd["id"]

        if "vertex_shader" in cmd:
            vertex_shader = base64.b64decode(cmd["vertex_shader"].encode('ascii')).decode('ascii')
            vertex_shader = adapt_vertex_shader(vertex_shader)
            #print(vertex_shader)
        if "fragment_shader" in cmd:
            fragment_shader = base64.b64decode(cmd["fragment_shader"].encode('ascii')).decode('ascii')
            #print(fragment_shader)
        if "uniforms" in cmd:
            uniforms = msgpack.unpackb(base64.b64decode(cmd["uniforms"].encode('ascii')))
        if "attributes" in cmd:
            attributes = msgpack.unpackb(base64.b64decode(cmd["attributes"].encode('ascii')))

        draw_mode = "triangle_strip"
        if "draw_mode" in cmd:
            draw_mode = cmd["draw_mode"]
        rows = 0 #meaning all rows
        if "rows" in cmd:
            rows = cmd["rows"]
        cols = 0 #all colls
        if "cols" in cmd:
            cols = cmd["cols"]

        # inject the time uniform
        try:
            self.program = factory.create_program(vertex_shader, fragment_shader)
            self.is_active = False
        except Exception as exc:
            print("exception while creating program: ", exc)
            return

        for key, value in attributes.items():
            #print("attr: ", key, value)
            self.program[key.decode('ascii')] = value
            #program[key] = value

        for key, value in uniforms.items():
            #print("unif: ", key, value)
            self.program[key.decode('ascii')] = value

        has_time = False
        has_mouse = False
        has_resolution = False
        for uniform in self.program.get_uniforms():
            if 'time' == uniform[0]:
                has_time = True
            if 'mouse' == uniform[0]:
                has_mouse = True
            if 'resolution' == uniform[0]:
                has_resolution = True

        self.cols = cols
        self.rows = rows
        self.has_time = has_time
        self.start_time = time.time()
        self.has_mouse = has_mouse
        self.has_resolution = has_resolution
        self.first_row = 0
        self.draw_mode = draw_mode

        self.is_sane = True

    def update_viewport(self):
        view_width = 2 * self.cols / self.progman.screen_cols
        view_height = 2 * self.rows / self.progman.screen_rows
        viewport = (-1,
                1 - 2.0 * (self.last_row - 1)/self.progman.screen_rows,
                view_width,
                view_height)
        self.program["viewport"] = viewport

    def draw(self, time_now, mouse):
        if self.has_time:
            self.program["time"] = time_now - self.start_time
        if self.has_mouse:
            program['mouse'] = mouse
        if self.is_active:
            self.program.draw(self.program.to_gl_constant(self.draw_mode))


class ProgramManager:
    def __init__(self, factory, screen_width, screen_height, char_width, char_height):
        self.factory = factory
        self.scale = 0
        self.screen_rows = 0
        self.screen_cols = 0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.char_width = char_width
        self.char_height = char_height
        self.prog_wraps = {}

    def process_cmd(self, cmd):
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
        program = self.prog_wraps[internal_id]
        program.last_row = row
        program.update_viewport()
        program.is_active = True


