ArtSciTerm protocol
========

## Status
Draft

## Introduction

This document wants to describe the protocol used to communicate between the client (guest) and ArtSciTerm terminal (host). The communication is at the moment mainly unidirectional where the client application is sending commands through ANSI escape sequences.


## Design forces

We want to keep it simple however we want to allow enough flexibility to cover a huge amount of usecases. Most of the forces are dictated by the usecases we would like to implement. Such usecases would be:
* Create/Update program with optional arguments. Such arguments would be:
  * id
  * title
  * vertex shader
  * fragment shader
  * dictionary of attributes
  * dictionary of uniforms
  * display mode
* Delete program identified by id
* Create/Update shader
* Create/Update dictionary of attributes or uniforms

As the communication is mainly unidirectional, the client program cannot check the success of the commands, but this should not cause any serious issues.

It does not make to much sense to have separately Create and Update commands. In order to avoid confusion, we will call the command cr(eate)update, thus crupdate.


## Envelope
The commands are sent in a Json like dictionary.

For details see examples/client_lib.py

## Commands


For details see examples/client_lib.py
