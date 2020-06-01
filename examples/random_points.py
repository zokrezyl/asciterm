#!/usr/bin/env python3
import base64
import msgpack
import time
import sys
import numpy as np


vertex_shader = """
attribute vec2 position;


void main() {
    gl_PointSize = 1;
    gl_Position = vec4(position.x, position.y, 0, 1.0);
}
"""

fragment_shader = """
uniform float time;
uniform vec3 color;
void main() {
    gl_FragColor = vec4(sin(time), sin(time/2), sin(time/3), 1.0);
    //gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
"""


def transcode(what):
    return base64.b64encode(what.encode('ascii')).decode('ascii')

def envelope(cmd="create", draw_mode="trianglestrip", cols=80, rows=12, vertex_shader=None, fragment_shader=None,
             attributes=None, uniforms=None):

    ret = f"\033_Acmd='{cmd}',rows={rows},cols={cols},draw_mode='{draw_mode}'"
    if vertex_shader:
        ret += f",vertex_shader='{transcode(vertex_shader)}'"

    if fragment_shader:
        ret += f",fragment_shader='{transcode(fragment_shader)}'"

    if attributes:
        ret += f",attributes='{base64.b64encode(attributes).decode('ascii')}'"

    if uniforms:
        ret += f",uniforms='{base64.b64encode(uniforms).decode('ascii')}'"

    ret += "\033\\"

    return ret


def main():

    data = np.random.uniform(-1.0, 1.0, size=(20000, 2)).astype(np.float32).tolist()
    attributes = msgpack.packb({"position": data})

    print("first we just print some lines...\r\n"  * 5)
    print(envelope(
        cmd="create",
        draw_mode="points",
        rows=10,
        cols=60,
        vertex_shader=vertex_shader,
        fragment_shader=fragment_shader,
        attributes=attributes), end="")

    sys.stdout.flush()
    #time.sleep(100)

if __name__ == "__main__":
    main()
