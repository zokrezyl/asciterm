#version 120

// Uniforms
// --------
uniform sampler2D tex_data;
uniform vec2 tex_size;
uniform float char_width;
uniform float char_height;
//uniform float rows;
uniform float cols;
uniform float scale;
//uniform vec2 selection;
//uniform vec4 foreground;


// Varyings
// --------
varying vec2 v_texcoord;
//varying vec4 v_background;
//varying vec4 v_foreground;
varying vec4 v_fg;
varying vec4 v_bg;


// Main
// ----
void main(void)
{
    vec2 uv = floor(gl_PointCoord.xy * char_height);
    if(uv.x > (char_width-1.0)) discard;
    if(uv.y > (char_height-1.0)) discard;
    float v = texture2D(tex_data, v_texcoord+uv/tex_size).r;
    gl_FragColor = v * v_fg + (1.0-v) * v_bg;
}
