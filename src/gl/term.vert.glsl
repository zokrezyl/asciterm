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
//uniform vec4 foreground;
//uniform vec4 background;
//uniform vec2 selection;
uniform mat4 projection;

// Attributes
// ----------
attribute float pindex;
attribute float gindex;
attribute vec4 fg;
attribute vec4 bg;


// Varyings
// --------
varying vec4 v_fg;
varying vec4 v_bg;
varying vec2 v_texcoord;
varying vec4 v_foreground;
varying vec4 v_background;


// Main
// ----
void main (void)
{
    // Compute char position from pindex
    float x = mod(pindex, cols);
    float y = floor(pindex/cols);
    vec2 P = (vec2(x,y) * vec2(char_width, char_height)) * scale;
    P += vec2(char_height, char_height)*scale/2.0;
    P += vec2(2.0, 2.0);
    gl_Position = projection*vec4(P, 0.0, 1.0);
    gl_PointSize = char_height * scale ;

    v_fg = fg.yzwx;
    v_bg = bg.yzwx;

    float n = tex_size.x/char_width;
    x = 0.5 +  mod(gindex, n) * char_width;
    y = 0.5 + floor(gindex/n) * char_height;
    v_texcoord = vec2(x/tex_size.x, y/tex_size.y);
}
