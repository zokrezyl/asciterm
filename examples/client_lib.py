import msgpack
import base64
import os

def transcode(what):
    return base64.b64encode(what.encode('ascii')).decode('ascii')

def envelope(title="untitled", cmd="create", draw_mode="trianglestrip", start_col = 10, cols=80, rows=12, vertex_shader=None, fragment_shader=None,
             attributes=None, uniforms=None):

    term = os.environ.get('TERM', 'else')
    print(term)
    if term == 'tmux':
        ret = f"\033Ptmux;\033\033"
    else:
        ret = f"\033"

    ret += f"_Atitle='{title}',cmd='{cmd}',start_col={start_col},rows={rows},cols={cols},draw_mode='{draw_mode}'"
    if vertex_shader:
        ret += f",vertex_shader='{transcode(vertex_shader)}'"

    if fragment_shader:
        ret += f",fragment_shader='{transcode(fragment_shader)}'"

    if attributes:
        attributes = msgpack.packb(attributes)
        ret += f",attributes='{base64.b64encode(attributes).decode('ascii')}'"

    if uniforms:
        ret += f",uniforms='{base64.b64encode(uniforms).decode('ascii')}'"

    if term == 'tmux':
        ret += "\033\033\\\033\\"
    else:
        ret += "\033\\"

    magic_string_s = "this-is-a-magic-string-for-whatever, id: "
    prog_id = 0
    ret += f"{magic_string_s}{prog_id:08}\r\n" * rows
    
    return ret
