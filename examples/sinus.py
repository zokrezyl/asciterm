#!/usr/bin/env python3
import time
import sys
import math
import numpy as np

from client_lib import envelope

vertex_shader = """
#define M_PI 3.1415926535897932384626433832795
$vertex_shader_variables;
attribute float number;

void main() {
    gl_PointSize = 1;
    gl_Position = vec4(2*number/10000 - 1, sin(64 * M_PI * number/10000), cos(64 * M_PI * number/10000), 1.0);
    $vertex_shader_epilog;
}
"""

fragment_shader = """
$fragment_shader_variables;
uniform float time;
uniform vec3 color;
void main() {
    gl_FragColor = vec4(sin(time), sin(time/2), sin(time/3), 1.0);
    //gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
"""


def main():

    number = [ v for v in range(10000)]
    attributes = {"number": number}

    print("first we just print some lines...\r\n"  * 5)
    print(envelope(
        cmd="create",
        draw_mode="points",
        rows=10,
        cols=160,
        vertex_shader=vertex_shader,
        fragment_shader=fragment_shader,
        attributes=attributes), end="")

    sys.stdout.flush()
    #time.sleep(100)

if __name__ == "__main__":
    main()
