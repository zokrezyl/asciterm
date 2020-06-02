#!/usr/bin/env python3
import sys
import time
from client_lib import envelope

# based on https://thebookofshaders.com/12/

vertex_shader = """
$vertex_shader_variables;
attribute vec2 position;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
    $vertex_shader_epilog;
}
"""

fragment_shader = """
$fragment_shader_variables;

void main() {
    $fragment_shader_prolog;
    vec2 st = relFragCoord.xy/viewport.zw;
    st.x *= viewport.z/viewport.w;

    vec3 color = vec3(.0);

    // Cell positions
    vec2 point[5];
    point[0] = vec2(0.83,0.75);
    point[1] = vec2(0.60,0.07);
    point[2] = vec2(0.28,0.64);
    point[3] = vec2(0.31,0.26);
    point[4] = mousePos/viewport.zw;

    float m_dist = 1 + (1 + sin(time))/100;  // minimum distance

    // Iterate through the points positions
    for (int i = 0; i < 5; i++) {
        float dist = distance(st, point[i]);

        // Keep the closer distance
        m_dist = min(m_dist, dist);
    }

    // Draw the min distance (distance field)
    color += m_dist;

    // Show isolines
    //color -= step(.7,abs(sin(50.0*m_dist)))*.3;
    gl_FragColor = vec4(color * (1 + (1 + sin(time)) / 2 ),1.0);
}
"""

def main():
    attributes = {
        'position': [(-1,-1), (-1, 1), ( 1,-1), ( 1, 1)]}

    print("first we just print some lines...\r\n"  * 5)
    print(envelope(
        title="voronoi",
        cmd="create",
        draw_mode="triangle_strip",
        start_col = 10,
        rows=35,
        cols=80,
        vertex_shader=vertex_shader,
        fragment_shader=fragment_shader,
        attributes=attributes), end="")

    sys.stdout.flush()
    if len(sys.argv) > 1:
        time.sleep(float(sys.argv[1]))

if __name__ == "__main__":
    main()
