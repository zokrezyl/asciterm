#version 120
uniform vec4 color;
uniform float time;
void main()
{
    gl_FragColor = vec4(1.0*sin(time), 0.7*cos(2*time), 0.7, 0.2);
} 
