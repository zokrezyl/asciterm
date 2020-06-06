import numpy as np
import os


class ArtSciTermFont:
    def __init__(self, self_path):
        self.data_dir = os.path.join(self_path, "data")

        self.char_width = 6.0
        self.char_height = 13.0
        regular = self.load_font("6x13-regular.npy")
        italic = self.load_font("6x13-italic.npy")
        bold = self.load_font("6x13-bold.npy")
        n1 = len(regular)
        n2 = len(italic)
        n3 = len(bold)
        n = n1+n2+n3
        dtype = [("code", np.uint32, 1),
                 ("data", np.uint8, 10)]
        font = np.zeros(n, dtype)
        font[:n1] = regular
        font[n1:n1+n2] = italic
        font[n1:n1+n2]["code"] += 1*65536
        font[n1+n2:n1+n2+n3] = bold
        font[n1+n2:n1+n2+n3]["code"] += 2*65536
        font["data"][0] = font["data"][1]  # we set the character of space for zero

        # Build a texture out of glyph arrays (need to unpack bits)
        # This code is specific for a character size of 6x13
        n = len(font)
        G = np.unpackbits(font["data"].ravel())
        G = G.reshape(n, 80)[:, :78].reshape(n, 13, 6)

        self.t_width, self.t_height = 6*128, 13*((n//128)+1)
        data = np.zeros((self.t_height, self.t_width), np.ubyte)

        for i in range(n):
            r = 13*(i//128)
            c = 6*(i % 128)
            data[r:r+13, c:c+6] = G[i]*255

        # Store char codes
        self._codes = font["code"]
        self.data = data

    def load_font(self, name):
        return np.load(os.path.join(self.data_dir, name))


