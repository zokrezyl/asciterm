For early suggestions, critics please add comments to https://github.com/zokrezyl/asciterm/issues/2

# ArtSciTerm: OpenGL Terminal 2.0 for Artists, Scientists and Engineers

![demo1](demo1.gif)
You should see a GIF demo above, but probably due to it's size github may throttle it, please click https://github.com/zokrezyl/asciterm/blob/master/demo1.gif


## Status
* (please see terminology at the end of this README)
* Under develeopment
* As you can see on the gif above lot of functionalities are already implemented
  * [x] scrolling with the mouse-wheel
  * [x] scrolling OpenGL programs
  * [ ] absolute positioning of programs
  * [ ] commands for updating existing programs
  * [ ] higher level of primitives like drawing lines, graphs etc
  * [ ] plugin mechanism that allow further higher level primitives
  * [ ] plugin mechanism that makes programs attributes like CPU usage, Disk usage etc. that would allow simpler clients

## What kind of problems do I want to solve
Over 20 years ago it was possible to draw lovely graphics on the terminal. One of the greatest fun was to create complex 2D/3D graphics on these terminals. The windows paradigm started to catch-up in the meantime, sentencing almost do death the evolution of terminals. They kept being dumbp terminals, just for simple purposes as text viewing and editing.
While transforming a terminal completely into a HTML/PDF like rich text display is not simple task, however simple things can be done like:
* Visualise dynamic and static graphs, charts, simple rich text
* Visualise remote graphs. Remember, ArtSciTerm is just processing some extended ANSI escape sequances that could be send by a remote machine while you are connected over ssh
* Display art
* Display complex graphics etc
* Do photo processing flows (if you know Darktable, running filters and displaying results in the terminal)

Several tool authors identify the need for text input inside their tools and often they end up reinventing/reimplementing the complex input (think emacs/vi modi) patterns. Or other annoyances you can see in tools like gnuplot where you have on one screen entering commands and on another one visualizing. Why not doing the same in the same terminal?

The main objective of ArtSciTerm is mainly to optimize certain workflows where text can be together with graphics without the need of complexity of HTML/javascript etc. However.. why not? I could be easily possible to think to rendel HTML on the terminal as well at a certain moment.



## Main ingredients
* vispy and/or glumpy (both are supported)
* libvterm
* links to come
* plannig to implement the terminal itself in C++ for even faster rendering

## Design
While the author wanted to implemented such a terminal over the past years, it seemed to be a complex task. However bumping into libvterm, as well some Python ctype wrappers arround libvterm and in the glumpy terminal example, we realized that it would be relatively easy to sew them together. So came into being ArtSciTerm.

Basically ArtSciTerm:
* renders libvterm on OpenGL canvas, by sending indexes in a 2D texture of the font glyphs when the terminal state changes
* the "pty" reader, before sending the text to libvterm for processing, pre-processes it and extracts the special ANSI escapes sequences that are carrying special ArtSciTerm commands for creating/updating/deleting OpenGL programs (shaders, their attributes and uniforms). After removing the special ANSI sequences, special "placeholder" strings are injected which whill be recognized in the libvterm rendered text as being placeholders for the OpenGL programs. When finally rendered on OpenGL canvas, this placeholder text is removed, the rest of the text is displayed, and on top of it the program is rendered.

## Future
* is bright


## Design ideas
* TODO

## Terminology
* program: OpenGL/ArtSciTerm program that is rendered in a portion of the screen consinting o Shaders 
* shader: please read OpenGL documentation
* shader attribute: read OpenGL documentation
