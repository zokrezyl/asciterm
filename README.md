# ArtSciTerm: OpenGL Terminal 2.0 for Artists, Scientists and Engineers


## What kind of problems do I want to solve
* create a rich terminal like iPython/Jupyter where
* I can instantly see graphics/visuals
* That can render fast
* Without leaving the terminal
* And maybe display rich text
* Display art
* Display complex graphics etc
* Do photo processing (if you know Darktable, running filters and displaying results in the terminal)


## How?
* Well, if you solve most of your daily problems with a terminal you know what it means
* If you used vispy or glumpy or other tools like that you start to get inspired


## Status
* Under develeopment

## Main ingredients
* vispy 
* or glumpy (both are supported)
* libvterm
* links to come

## Future
* Displaying instant graphs/graphics is still under work
* Even this documentation is under work


## Design ideas
* create an ansi escape extension that allows by writing to stdout
    * to send shaders, uniforms and attributes to the OpenGL engine
    * run shaders
    * update uniforms and attributes


