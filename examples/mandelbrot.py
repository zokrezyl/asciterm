#!/usr/bin/env python3
import time
import sys
import numpy as np
from client_lib import envelope

# Shader source code: from https://github.com/vispy/vispy/blob/master/examples/demo/gloo/mandelbrot.py
# -----------------------------------------------------------------------------
vertex_shader = """
$vertex_shader_variables;
attribute vec2 position;
attribute vec2 texcoord;
varying vec2 v_texcoord;
varying float v_zoom;
varying float v_depth;
void main()
{
    gl_Position = vec4(position.x, position.y, 0.0, 1.0);
    v_texcoord = texcoord;
    v_zoom = 1.0/pow(2, (1.01 + sin(time/8))*8);
    v_depth = 400.0 * (2 + sin(time/8)) - 400;
    $vertex_shader_epilog;
}
"""

fragment_shader = """
$fragment_shader_variables;

varying vec2 v_texcoord;
varying float v_zoom;
varying float v_depth;

vec3 hot(float t)
{
    return vec3(smoothstep(0.00,0.33,t),
                smoothstep(0.33,0.66,t),
                smoothstep(0.66,1.00,t));
}

void main()
{
    const float log_2 = 0.6931471805599453;
    vec2 c = v_zoom * v_texcoord  - vec2( ( 2.5 + v_zoom )/ 2.0, 0.01);

    float n = v_depth;

    float x, y, d;
    int i;
    vec2 z = c;
    for(i = 0; i < n; ++i)
    {
        x = (z.x*z.x - z.y*z.y) + c.x;
        y = (z.y*z.x + z.x*z.y) + c.y;
        d = x*x + y*y;
        if (d > 4.0) break;
        z = vec2(x,y);
    }

    if ( i < n ) {
        float nu = log(log(sqrt(d))/log_2)/log_2;
        float index = float(i) + 1.0 - nu;
        float v = pow(index/float(n),0.5);
        gl_FragColor = vec4(hot(v),1.0);
    } else {
        gl_FragColor = vec4(hot(0.0),1.0);
    }
}
"""


def main():
    attributes = {
        'position': [(-1,-1), (-1, 1), ( 1,-1), ( 1, 1)],
        'texcoord': [( -1, 1), ( -1, -1), ( 1, 1), ( 1, -1)]}

    print("first we just print some lines...\r\n"  * 5)
    print(envelope(
        cmd="create",
        draw_mode="triangle_strip",
        rows=15,
        cols=180,
        vertex_shader=vertex_shader,
        fragment_shader=fragment_shader,
        attributes=attributes), end="")

    sys.stdout.flush()
    if len(sys.argv) > 1:
        time.sleep(float(sys.argv[1]))

if __name__ == "__main__":
    main()
