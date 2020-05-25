#!/usr/bin/env python3
import base64
import msgpack

# Shader source code: from https://github.com/vispy/vispy/blob/master/examples/demo/gloo/mandelbrot.py
# -----------------------------------------------------------------------------
vertex_shader = """
attribute vec2 position;

void main()
{
    gl_Position = vec4(position, 0, 1.0);
}
"""

fragment_shader = """
uniform vec2 center;
uniform vec2 mouse;

uniform float time;

vec3 hot(float t)
{
    float retime = 100;

    return vec3(sin(4*retime/7)*smoothstep(0.00,0.33,t),
                sin(4*retime/5)*smoothstep(0.33,0.66,t),
                sin(4*retime/3)*smoothstep(0.66,1.00,t));
}

void main()
{
    const int n = 300;
    const float log_2 = 0.6931471805599453;

    vec2 c;

    float rescale;
    //rescale = 0.2*sin(time/17);
    rescale = 1;

    //vec2 center = vec2(2*sin(2*time)*center.x, 3*sin(3*time)*center.y);
    vec2 center = mouse;


    // Recover coordinates from pixel coordinates
    c.x = (gl_FragCoord.x / 1000 ) * rescale - center.x + 0.5;
    c.y = (gl_FragCoord.y / 1000 ) * rescale - center.y;

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

def envelope(rows=12, vertex_shader=None, fragment_shader=None,
             attributes=None, uniforms=None):

    ret = f"\033_Arows={rows}"
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
            "position": [(-1, -1), (-1, 1), (1, 1),
                                    (-1, -1), (1, 1), (1, -1)]})

    print(envelope(
        rows=1,
        vertex_shader=vertex_shader,
        fragment_shader=fragment_shader,
        attributes=attributes), end="")



if __name__ == "__main__":
    main()
