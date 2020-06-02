import msgpack
import base64

def transcode(what):
    return base64.b64encode(what.encode('ascii')).decode('ascii')

def envelope(title="untitled", cmd="create", draw_mode="trianglestrip", start_col = 10, cols=80, rows=12, vertex_shader=None, fragment_shader=None,
             attributes=None, uniforms=None):

    ret = f"\033_Atitle='{title}',cmd='{cmd}',start_col={start_col},rows={rows},cols={cols},draw_mode='{draw_mode}'"
    if vertex_shader:
        ret += f",vertex_shader='{transcode(vertex_shader)}'"

    if fragment_shader:
        ret += f",fragment_shader='{transcode(fragment_shader)}'"

    if attributes:
        attributes = msgpack.packb(attributes)
        ret += f",attributes='{base64.b64encode(attributes).decode('ascii')}'"

    if uniforms:
        ret += f",uniforms='{base64.b64encode(uniforms).decode('ascii')}'"

    ret += "\033\\"
    return ret
