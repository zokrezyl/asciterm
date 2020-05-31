import time
import base64
import base64
import msgpack
import numpy as np
#import msgpack_numpy as m

#m.patch()


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
        self.programs = {}
        self.active = False

    def adapt_vertex_shader(self, vertex_shader):
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


    def process_cmd(self, cmd):
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
            vertex_shader = self.adapt_vertex_shader(vertex_shader)
        if "fragment_shader" in cmd:
            fragment_shader = base64.b64decode(cmd["fragment_shader"].encode('ascii')).decode('ascii')
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
        program = self.factory.create_program(vertex_shader, fragment_shader)

        for key, value in attributes.items():
            program[key.decode('ascii')] = value
            #program[key] = value

        for key, value in uniforms.items():
            program[key.decode('ascii')] = value

        has_time = False
        has_mouse = False
        for uniform in program.get_uniforms():
            if 'time' == uniform[0]:
                has_time = True
            if 'mouse' == uniform[0]:
                has_mouse = True
        setattr(program, "cols", cols)
        setattr(program, "rows", rows)
        setattr(program, "has_time", has_time)
        setattr(program, "start_time", time.time())
        setattr(program, "has_mouse", has_mouse)
        setattr(program, "first_row", 0)
        setattr(program, "draw_mode", draw_mode)
        self.programs[cmd["internal_id"]] = program


    def on_screen_size_change(self, scale, cols, rows, width, height):
        self.scale = scale
        self.screen_cols = cols
        self.screen_rows = rows
        self.screen_width = width
        self.screen_height = height
        for key, program in self.programs.items():
            self.update_program_viewport(program)


    def update_program_viewport(self, program):
        view_width = 2 * program.cols / self.screen_cols
        view_height = 2 * program.rows / self.screen_rows
        viewport = (-1,
                1 - 2.0 * (program.last_row - 1)/self.screen_rows,
                view_width,
                view_height)
        program["viewport"] = viewport


    def set_prog_last_row(self, internal_id, row):
        print("set_prog_last_row ", internal_id, row)
        program = self.programs[internal_id]
        program.last_row = row
        self.update_program_viewport(program)
        program.active = True


