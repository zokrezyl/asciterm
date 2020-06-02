""" 
based on https://github.com/powerline/powerline/blob/master/tests/modules/lib/vterm.py
see LICENSE in the same  folder
"""

import subprocess
import os


from ctypes import (
    cast,
    c_char_p,
    c_void_p,
    c_uint,
    c_size_t,
    c_char,
    c_int,
    c_uint8,
    c_uint32,
    py_object,
    LibraryLoader,
    CFUNCTYPE,
    CDLL,
    POINTER,
    Structure,
    Union,
    )


class CTypesFunction(object):
    def __init__(self, library, name, rettype, args):
        self.name = name
        self.args = args
        self.prototype = CFUNCTYPE(rettype, *[
                arg[1] for arg in args
        ])
        self.func = self.prototype((name, library), tuple((
                (1, arg[0]) for arg in args
        )))

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return '{cls}(<library>, {name!r}, {rettype!r}, {args!r})'.format(
                cls=self.__class__.__name__,
                **self.__dict__
        )


class CTypesLibraryFuncsCollection(object):
    def __init__(self, lib, **kwargs):
        self.lib = lib
        library_loader = LibraryLoader(CDLL)
        library = library_loader.LoadLibrary(lib)
        self.library = library
        for name, args in kwargs.items():
            self.__dict__[name] = CTypesFunction(library, name, *args)


class VTermColor_s(Structure):
    _fields_ = (
            ('type', c_uint8),
            ('red', c_uint8),
            ('green', c_uint8),
            ('blue', c_uint8),
    )


class VTermPos_s(Structure):
    _fields_ = (
            ('row', c_int),
            ('col', c_int),
    )


class VTermScreenCellAttrs_s(Structure):
    _fields_ = (
            ('bold', c_uint, 1),
            ('underline', c_uint, 2),
            ('italic', c_uint, 1),
            ('blink', c_uint, 1),
            ('reverse', c_uint, 1),
            ('strike', c_uint, 1),
            ('font', c_uint, 4),
            ('dwl', c_uint, 1),
            ('dhl', c_uint, 2),
    )


VTERM_MAX_CHARS_PER_CELL = 6


class VTermScreenCell_s(Structure):
    _fields_ = (
            ('chars', c_char*VTERM_MAX_CHARS_PER_CELL),
            ('width', c_char),
            ('attrs', VTermScreenCellAttrs_s),
            ('fg', VTermColor_s),
            ('bg', VTermColor_s),
    )


VTerm_p = c_void_p
VTermState_p = c_void_p


class ScreenPen_prop_s(Structure):
    _fields_ = [
            ('bold', c_int, 1),
            ('underline', c_int, 2),
            ('italic', c_int, 1),
            ('blink', c_int, 1),
            ('reverse', c_int, 1),
            ('strike', c_int, 1),
            ('font', c_int, 4)]


class ScreenPen_other_s(Structure):
    _fields_ = [
            ('protected_cell', c_int, 1),
            ('dwl', c_int, 1),
            ('dhl', c_int, 2)]


class ScreenPen_s(Structure):
    _fields_ = (
            ('fg', VTermColor_s),
            ('bg', VTermColor_s),
            ('rest', c_uint32))


class ScreenCell_s(Structure):
    _fields_ = (
            ('chars', c_uint32 * VTERM_MAX_CHARS_PER_CELL),
            ('fg', c_uint8*4),
            ('bg', c_uint8*4),
            ('__', c_uint32))


class VTermRect_s(Structure):
    _fields_ = (
        ('start_row', c_int),
        ('end_row', c_int),
        ('start_col', c_int),
        ('end_col', c_int))

User_p = py_object
VTermValue_p = c_void_p


class VTermValue_u(Union):
    _fields_ = (
          ('boolean', c_int),
          ('number', c_int),
          ('string', c_char_p),
          ('color', VTermColor_s),)


class VTermScreenCallbacks_s(Structure):
    damage_f = CFUNCTYPE(c_int, VTermRect_s, User_p)
    moverect_f = CFUNCTYPE(c_int, VTermRect_s, VTermRect_s, User_p)
    movecursor_f = CFUNCTYPE(c_int, VTermPos_s, VTermPos_s, c_int, User_p)
    settermprop_f = CFUNCTYPE(c_int, c_int, POINTER(VTermValue_u), User_p)
    bell_f = CFUNCTYPE(c_int, User_p)
    resize_f = CFUNCTYPE(c_int, c_int, c_int, POINTER(VTermPos_s), User_p)
    sb_pushline_f = CFUNCTYPE(c_int, c_int, POINTER(VTermScreenCell_s), User_p)
    sb_popline_f = CFUNCTYPE(c_int, c_int, POINTER(VTermScreenCell_s), User_p)

    _fields_ = (
                ('damage', damage_f),
                ('moverect', moverect_f),
                ('movecursor', movecursor_f),
                ('settermprop', settermprop_f),
                ('bell', bell_f),
                ('resize', resize_f),
                ('sb_pushline', sb_pushline_f),
                ('sb_popline', sb_popline_f))


class VTermScreen_s(Structure):
   _fields_ = (
          ('vt', c_void_p),
          ('state', c_void_p),
          ('callbacks', POINTER(VTermScreenCallbacks_s)),
          ('cbdata', c_void_p),
          ('damagesize', c_int),
          ('damaged', VTermRect_s),
          ('pending_scrollrect', VTermRect_s),
          ('pending_scroll_downward', c_int),
          ('pending_scroll_rightward', c_int),
          ('rows', c_int),
          ('cols', c_int),
          ('global_reverse', c_int),
          ('buffers', POINTER(ScreenCell_s)*2),
          ('buffer', POINTER(ScreenCell_s)),
          ('sb_buffer', c_void_p),
          ('pen', ScreenPen_s))


VTermScreen_p = POINTER(VTermScreen_s)


def get_functions(lib):
    return CTypesLibraryFuncsCollection(
        lib,
        vterm_new=(VTerm_p, (
                ('rows', c_int),
                ('cols', c_int)
        )),
        vterm_obtain_screen=(VTermScreen_p, (('vt', VTerm_p),)),
        vterm_set_size=(None, (
                ('vt', VTerm_p),
                ('rows', c_int),
                ('cols', c_int)
        )),
        vterm_screen_reset=(None, (
                ('screen', VTermScreen_p),
                ('hard', c_int)
        )),
        vterm_input_write=(c_size_t, (
                ('vt', VTerm_p),
                ('bytes', POINTER(c_char)),
                ('size', c_size_t),
        )),
        vterm_screen_get_cell=(c_int, (
                ('screen', VTermScreen_p),
                ('pos', VTermPos_s),
                ('cell', POINTER(VTermScreenCell_s))
        )),
        vterm_screen_set_callbacks=(None, (
                ('screen', VTermScreen_p),
                ('callbacks', POINTER(VTermScreenCallbacks_s)),
                ('user', User_p),
        )),
        vterm_screen_enable_altscreen=(None, (
                ('screen', VTermScreen_p),
                ('altscreen', c_int),
        )),
        vterm_screen_set_damage_merge=(None, (
                ('screen', VTermScreen_p),
                ('damage_size', c_int),
        )),
        vterm_free=(None, (
            ('vt', VTerm_p),
        )),
        vterm_state_get_cursorpos=(None, (
            ('state', VTermState_p),
            ('pos', POINTER(VTermPos_s))
        )),
        vterm_obtain_state=(VTermState_p, (
            ('term', VTerm_p),
        )),
        vterm_set_utf8=(None, (('vt', VTerm_p), ('is_utf8', c_int))),
    )


class VTerm(object):

    VTERM_PROP_CURSORVISIBLE = 1 ,# bool
    VTERM_PROP_CURSORBLINK =2       # bool
    VTERM_PROP_ALTSCREEN =3         # bool
    VTERM_PROP_TITLE = 4             # string
    VTERM_PROP_ICONNAME = 5          # string
    VTERM_PROP_REVERSE = 6           # bool
    VTERM_PROP_CURSORSHAPE = 7       # number
    VTERM_PROP_MOUSE = 8             # number


    VTERM_DAMAGE_CELL = 0,    # every cell 
    VTERM_DAMAGE_ROW  =  1    # entire rows 
    VTERM_DAMAGE_SCREEN = 2  # entire screen
    VTERM_DAMAGE_SCROLL = 3  # entire screen + scrollrect 
    def find_in_ld_cache(self):
        ret = None
        try:
            ret = subprocess.run(["ldconfig", "-p"], stdout=subprocess.PIPE)
        except Exception as exc:
            print("ldcache -p failed: ", exc)
            return None
        if ret.stdout is None:
            print("ldcache -p failed")

        ld_cache = ret.stdout.decode('ascii').split('\n')
        for line in ld_cache:
            if "libvterm" in line:
                line = line.split(" ")
                if len(line) < 4:
                    print(f"entry in ldconfig line not in expected format. (was expecting 4 fields) {line}")
                    return None
                if "libvterm" not in line[3]:
                    print(f"entry in ldconfig line not in expected format. (was expecting libvterm full path in 4th field) {line}")
                    return None
                return line[3]

    def find_libvterm(self, libvterm_path):
        if libvterm_path is not None:
            if os.path.isfile(libvterm_path):
                return libvterm_path
            lib_file = self.find_in_ld_cache()
            if lib_file is not None:
                print(f"could not find libvterm under the suggested path, but could find one at {lib_file}. Do not use the path argument or give the correct one")
            return None
        return self.find_in_ld_cache()

    def __init__(self, libvterm_path, rows, cols):
        # TODO .. implement a mechanism to find the right lib on the system
        # lib = "/usr/lib/x86_64-linux-gnu/libvterm.so.0.0.0"

        # lib = "/g/ext/libvterm/.libs/libvterm.so"
        lib = self.find_libvterm(libvterm_path)
        print(f"using lib {lib}")

        # lib = "/g/ext/libvterm/.libs/libvterm.so"
        # lib = "/usr/lib/x86_64-linux-gnu/libvterm.so.0.0.2"

        self.functions = get_functions(lib)
        self.vt = self.functions.vterm_new(rows, cols)
        self.functions.vterm_set_utf8(self.vt, 1)
        self.screen = self.functions.vterm_obtain_screen(self.vt)
        self.functions.vterm_screen_reset(self.screen, int(bool(True)))

        self.callbacks = VTermScreenCallbacks_s(
            #damage=VTermScreenCallbacks_s.damage_f(self._on_damage),
            movecursor=VTermScreenCallbacks_s.movecursor_f(self._on_movecursor),
            moverect=VTermScreenCallbacks_s.moverect_f(0),
            settermprop=VTermScreenCallbacks_s.settermprop_f(self._on_settermprop),
            bell=VTermScreenCallbacks_s.bell_f(0),
            resize=VTermScreenCallbacks_s.resize_f(0),
            sb_pushline=VTermScreenCallbacks_s.sb_pushline_f(0),
            sb_popline=VTermScreenCallbacks_s.sb_popline_f(0))

        self.functions.vterm_screen_set_callbacks(self.screen, self.callbacks, None)
        self.functions.vterm_screen_enable_altscreen(self.screen, 1)
        self.functions.vterm_screen_set_damage_merge(self.screen, VTerm.VTERM_DAMAGE_SCROLL)
        #self.functions.vterm_screen_set_damage_merge(self.screen, VTerm.VTERM_DAMAGE_SCREEN)
        self.cursor_pos = VTermPos_s()

    def _on_damage(self, rect, user):
        return self.on_damage(rect, user)

    def __on_damage(self, rect, user):
        return int(True)

    def _on_moverect(self, dest, src, user):
        return int(True)

    def _on_movecursor(self, pos, oldpos, visible, user):
        return self.on_movecursor(pos, oldpos, visible, user)

    def on_movecursor(self, pos, oldpos, visible, user):
        return int(True)

    def _on_bell(self, user):
        return int(True)

    def _on_settermprop(self, prop, val, user):
        # TODO .. use this to set the window title...
        if prop == VTerm.VTERM_PROP_ALTSCREEN:
            self.on_set_term_altscreen(val.contents.boolean)
        elif prop == VTerm.VTERM_PROP_TITLE:
            self.on_set_term_title(val.contents.string)
        return int(True)

    def _on_resize(self, new_rows, new_cols, delta, user):
        return int(True)

    def _on_sb_pushline(self, cols, cells, user):
        # TODO .. implement scrollback
        # save the cells into internal buffer
        return int(True)

    def _on_sb_popline(self, cols, cells, user):
        # TODO .. give back lines from buffer
        return int(False)

    def push(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self.functions.vterm_input_write(self.vt, data, len(data))

    def resize(self, rows, cols):
        self.functions.vterm_set_size(self.vt, rows, cols)

    def get_cursor_pos(self):
        term_state = self.functions.vterm_obtain_state(self.vt)
        self.functions.vterm_state_get_cursorpos(term_state, self.cursor_pos)
        return self.cursor_pos

    def __del__(self):
            try:
                    self.functions.vterm_free(self.vt)
            except AttributeError:
                    pass
