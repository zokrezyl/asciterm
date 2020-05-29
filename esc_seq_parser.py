import re

TOKEN_EOB = 0
TOKEN_COMMA = 1
TOKEN_EQUAL = 2
TOKEN_SEMICOLON = 3
TOKEN_LESS = 4
TOKEN_GREATER = 5
TOKEN_BEGIN_ASCITERM_SEQUENCE = 6
TOKEN_END_ASCITERM_SEQUENCE = 7
TOKEN_KEY = 8
TOKEN_STRING = 9
TOKEN_NUMBER = 10


token_dict = {
        TOKEN_EOB: 'TOKEN_EOB',
        TOKEN_COMMA: 'TOKEN_COMMA',
        TOKEN_EQUAL: 'TOKEN_EQUAL',
        TOKEN_SEMICOLON: 'TOKEN_SEMICOLON',
        TOKEN_LESS: 'TOKEN_LESS',
        TOKEN_GREATER: 'TOKEN_GREATER',
        TOKEN_BEGIN_ASCITERM_SEQUENCE: 'TOKEN_BEGIN_ASCITERM_SEQUENCE',
        TOKEN_END_ASCITERM_SEQUENCE: u'TOKEN_END_ASCITERM_SEQUENCE',
        TOKEN_KEY: 'TOKEN_KEY',
        TOKEN_STRING: 'TOKEN_STRING',
        TOKEN_NUMBER: 'TOKEN_NUMBER'}

BEGIN_ASCITERM_SEQUENCE = '\033_A'


class UnexpectedTokenException(Exception):
    pass

class Tokenizer:
    def __init__(self, buf):
        self.pos = 0
        self.buf = buf.decode('utf-8')
        self.size = len(self.buf)
        self.re_key_prog = re.compile(r"([a-zA-Z]\w*)")
        self.re_number_prog = re.compile(r"([a-zA-Z]\w*)")
        self.re_string_prog = re.compile(r"([a-zA-Z]\w*)")

    def lex_number(self):
        first = self.pos
        if self.buf[self.pos] == "-":
            self.pos += 1
        while self.buf[self.pos].isdigit() and self.pos < len(self.buf):
            self.pos += 1
        return int(self.buf[first: self.pos]) # TODO make 

    def lex_key(self):
        first = self.pos
        while (self.buf[self.pos].isalnum() or self.buf[self.pos] == '_') and self.pos < len(self.buf):
            self.pos += 1
        return self.buf[first: self.pos]

    def lex_string(self):
        first = self.pos
        quote_open = self.buf[self.pos]
        self.pos += 1  # skip beginning of string
        while self.pos < len(self.buf) and (self.buf[self.pos] != quote_open):
            self.pos += 1
        if self.pos == len(self.buf):
            raise Exception("string not ended")
        self.pos += 1
        return self.buf[first + 1: self.pos - 1]

    def next_token(self):
        if self.buf[self.pos] == '=':
            self.pos += 1
            return (TOKEN_EQUAL, '=')

        if self.buf[self.pos] == ',':
            self.pos += 1
            return (TOKEN_COMMA, ',')

        if self.buf[self.pos].isdigit():
            return (TOKEN_NUMBER, self.lex_number())

        if self.buf[self.pos] == '"':
            return (TOKEN_STRING, self.lex_string())

        if self.buf[self.pos] == "'":
            return (TOKEN_STRING, self.lex_string())

        if self.buf[self.pos].isalpha():
            return (TOKEN_KEY, self.lex_key())

        if self.buf[self.pos] == '\33':
            if (self.pos < self.size - 1):
                if self.buf[self.pos + 1] == '_':
                    if (self.pos < self.size - 2):
                        if self.buf[self.pos + 2] == 'A':
                            self.pos += 3
                            return (TOKEN_BEGIN_ASCITERM_SEQUENCE, BEGIN_ASCITERM_SEQUENCE)
                    return (TOKEN_END_ASCITERM_SEQUENCE, "\33\\")
                elif self.buf[self.pos + 1] == '\\':
                    self.pos += 2
                    return (TOKEN_END_ASCITERM_SEQUENCE, "\33\\")

        raise Exception(f"Unknown token '{self.buf[self.pos: self.pos+10]}' at {self.pos}")

    def find_next_begin_token(self):
        pos = self.buf.find(BEGIN_ASCITERM_SEQUENCE, self.pos)
        if pos == -1:
            self.pos = len(self.buf)
            return (TOKEN_EOB, None)
        self.pos = pos
        return (TOKEN_BEGIN_ASCITERM_SEQUENCE, BEGIN_ASCITERM_SEQUENCE)


class BufferProcessor:
    """ processes chunks of input and hunting for asciterm escape sequences
        the processor is feed with chunks through the process method
        a sequence may start in one chunk and continue in the next one
        and so on...

    """

    magic_string = b"this-is-a-magic-string-for-whatever, id: "
    magic_string_s = magic_string.decode('ascii')
    def __init__(self):
        self.last_program_id = 0

    def process_key_value(self):
        token = self.tokenizer.next_token()
        if token[0] != TOKEN_KEY:
            raise Exception(f"unexpected token, got {token_dict[token[0]]}, expected {token_dict[TOKEN_KEY]} {token[1]}")
        key = token[1]
        token = self.tokenizer.next_token() 
        if token[0] != TOKEN_EQUAL:
            raise Exception(f"unexpected token, got {token_dict[token[0]]}, expected {token_dict[TOKEN_EQUAL]} {token[1]}")
        token = self.tokenizer.next_token()
        if token[0] != TOKEN_STRING and token[0] != TOKEN_NUMBER:
            raise Exception(f"unexpected token, got {token_dict[token[0]]}, expected {token_dict[TOKEN_STRING]} or {token_dict[TOKEN_NUMBER]} {token[1]}")
        value = token[1]
        return (key, value)

    def process_cmd(self):
        cmd = {}
        token = self.tokenizer.next_token()
        if token[0] != TOKEN_BEGIN_ASCITERM_SEQUENCE:
            raise Exception("expected begin asciterm sequence")
        while True:
            (key, value) = self.process_key_value()
            cmd[key] = value
            token = self.tokenizer.next_token()
            if token[0] == TOKEN_END_ASCITERM_SEQUENCE:
                return cmd
            if token[0] != TOKEN_COMMA:
                raise Exception(f"unexpected token, got {token_dict[token[0]]}, expected {token_dict[TOKEN_COMMA]} {token[1]}")

    def process(self, buf):
        """ we are looking for sequences with escape codes like <ESC>_A<key1>=<value1>,<key2>=<value2><ESC>\
        """
        self.buf = buf
        self.tokenizer = Tokenizer(buf)
        self.cmds = []

        ret = bytes()

        cmds = []
        prev = 0
        while True:
            token = self.tokenizer.find_next_begin_token()
            if token[0] == TOKEN_EOB:
                ret += self.buf[prev: self.tokenizer.pos]
                return (cmds, ret)
            ret += self.buf[prev: self.tokenizer.pos]
            print("found cmd at ", self.tokenizer.pos)
            try:
                cmd = self.process_cmd()
                if "cmd" in cmd:
                    if cmd["cmd"] == "create" and "rows" in cmd:
                        #ret += ("\n"*cmd["rows"]).encode('ascii')
                        # We are insert this fake string as place marker for the cmd
                        # when we draw a new screen we will hunt for these strings in the vterm 
                        # and replace them with blanks and display over it the program
                        ret += (f"{self.magic_string_s}{self.last_program_id:08}\r\n"\
                                *cmd["rows"]).encode('ascii')
                        cmd["internal_id"] = self.last_program_id
                        self.last_program_id += 1
                    prev = self.tokenizer.pos
                    cmds.append(cmd)
            except Exception as e:
                raise e
                #TODO .. log print("exception ++", e, self.tokenizer.pos)
