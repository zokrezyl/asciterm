#!/usr/bin/env python3
import base64
import msgpack
import time
import sys
import numpy as np
#import msgpack_numpy as m

#m.patch()

# Shader source code: from https://github.com/vispy/vispy/blob/master/examples/demo/gloo/mandelbrot.py
# -----------------------------------------------------------------------------
vertex_shader = """
    attribute vec2 position;
    attribute vec2 texcoord;
    varying vec2 v_texcoord;
    varying float v_zoom;
    varying float v_depth;
    uniform float time;
    void main()
    {
        //gl_Position = <transform>;
        gl_Position = vec4(position.x, position.y, 0.0, 1.0);
        v_texcoord = texcoord;
        v_zoom = 1.0/pow(2, (1.01 + sin(time/8))*8);
        v_depth = 400.0 * (2 + sin(time/8)) - 400;
    }
"""

fragment_shader = """

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


def transcode(what):
    return base64.b64encode(what.encode('ascii')).decode('ascii')

def envelope(cmd="create", draw_mode="triangle_strip", cols=80, rows=12, vertex_shader=None, fragment_shader=None,
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
    attributes = msgpack.packb({
        'position': [(-1,-1), (-1, 1), ( 1,-1), ( 1, 1)],
        'texcoord': [( -1, 1), ( -1, -1), ( 1, 1), ( 1, -1)]})

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
    #time.sleep(100)

if __name__ == "__main__":
    main()
