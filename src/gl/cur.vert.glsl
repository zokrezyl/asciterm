#version 120
uniform float scale;
attribute vec2 position;
void main()
{
    //gl_Position = vec4(position, 0.0, 1)*scale;
    gl_Position = vec4(position, 0.0, 1);
} 
