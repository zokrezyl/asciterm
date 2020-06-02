#!/usr/bin/env python3
import time
import sys
import numpy as np

from client_lib import envelope

vertex_shader = """
attribute vec2 position;


void main() {
    gl_PointSize = 1;
    gl_Position = vec4(position.x, position.y, 0, 1.0);
}
"""

fragment_shader = """
void main() {
    gl_FragColor = vec4(sin(time), sin(time/2), sin(time/3), 1.0);
    //gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
"""


def main():

    data = np.random.uniform(-1.0, 1.0, size=(20000, 2)).astype(np.float32).tolist()
    attributes = {"position": data}

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
    if len(sys.argv) > 1:
        time.sleep(float(sys.argv[1]))


if __name__ == "__main__":
    main()
