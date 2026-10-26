"""Tiny standard-library PNG chart helpers for a dependency-free fallback."""

import struct
import zlib


FONT = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
}


class Canvas:
    def __init__(self, width=900, height=520):
        self.width = width
        self.height = height
        self.pixels = bytearray([255] * (width * height * 3))

    def pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset : offset + 3] = bytes(color)

    def line(self, x1, y1, x2, y2, color, thickness=1):
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        error = dx - dy
        while True:
            for ox in range(-thickness // 2, thickness // 2 + 1):
                for oy in range(-thickness // 2, thickness // 2 + 1):
                    self.pixel(x1 + ox, y1 + oy, color)
            if x1 == x2 and y1 == y2:
                break
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x1 += sx
            if doubled < dx:
                error += dx
                y1 += sy

    def rectangle(self, x1, y1, x2, y2, color):
        for y in range(max(0, y1), min(self.height, y2)):
            for x in range(max(0, x1), min(self.width, x2)):
                self.pixel(x, y, color)

    def text(self, x, y, value, color=(35, 45, 60), scale=2):
        for character in str(value).upper():
            glyph = FONT.get(character, FONT[" "])
            for row, bits in enumerate(glyph):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        self.rectangle(
                            x + column * scale,
                            y + row * scale,
                            x + (column + 1) * scale,
                            y + (row + 1) * scale,
                            color,
                        )
            x += 6 * scale

    def save(self, path):
        raw = b"".join(
            b"\x00" + bytes(self.pixels[y * self.width * 3 : (y + 1) * self.width * 3])
            for y in range(self.height)
        )

        def chunk(kind, payload):
            return (
                struct.pack(">I", len(payload))
                + kind
                + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
            )

        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">2I5B", self.width, self.height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
        with open(path, "wb") as output:
            output.write(png)


def bar_chart(path, title, labels, values, colors=None):
    canvas = Canvas()
    canvas.text(24, 20, title, scale=3)
    left, top, right, bottom = 105, 85, 860, 420
    maximum = max(values, default=0) or 1
    step = maximum / 4
    for tick in range(5):
        y = bottom - int((bottom - top) * tick / 4)
        canvas.line(left, y, right, y, (225, 230, 235))
        canvas.text(20, y - 5, f"{maximum * tick / 4:.0f}", scale=1)
    canvas.line(left, top, left, bottom, (55, 65, 80), 2)
    canvas.line(left, bottom, right, bottom, (55, 65, 80), 2)
    spacing = (right - left) / max(1, len(values))
    palette = colors or [(37, 99, 235)] * len(values)
    for index, (label, value) in enumerate(zip(labels, values)):
        x1 = int(left + spacing * index + spacing * 0.18)
        x2 = int(left + spacing * index + spacing * 0.82)
        y = bottom - int((bottom - top) * value / maximum)
        canvas.rectangle(x1, y, x2, bottom, palette[index % len(palette)])
        canvas.text(x1, bottom + 12, str(label)[:10], scale=1)
        canvas.text(x1, max(top, y - 17), f"{value:.0f}", scale=1)
    canvas.save(path)


def line_chart(path, title, series, labels):
    canvas = Canvas()
    canvas.text(24, 20, title, scale=3)
    left, top, right, bottom = 85, 85, 860, 420
    values = [value for values in series.values() for value in values]
    maximum = max(values, default=1) or 1
    minimum = min(0, min(values, default=0))
    span = maximum - minimum or 1
    for tick in range(5):
        y = bottom - int((bottom - top) * tick / 4)
        value = minimum + span * tick / 4
        canvas.line(left, y, right, y, (225, 230, 235))
        canvas.text(15, y - 4, f"{value:.0f}", scale=1)
    palette = [(5, 150, 105), (37, 99, 235), (217, 119, 6)]
    point_count = max((len(values) for values in series.values()), default=1)
    for series_index, (name, points) in enumerate(series.items()):
        coords = []
        for index, value in enumerate(points):
            x = left + int((right - left) * index / max(1, point_count - 1))
            y = bottom - int((bottom - top) * (value - minimum) / span)
            coords.append((x, y))
        for first, second in zip(coords, coords[1:]):
            canvas.line(*first, *second, palette[series_index % len(palette)], 3)
        for x, y in coords:
            canvas.rectangle(x - 3, y - 3, x + 4, y + 4, palette[series_index % len(palette)])
        canvas.text(left + 10 + series_index * 180, 465, name, palette[series_index % len(palette)], 2)
    if labels:
        stride = max(1, len(labels) // 8)
        for index in range(0, len(labels), stride):
            x = left + int((right - left) * index / max(1, point_count - 1))
            canvas.text(x - 15, bottom + 12, labels[index][:8], scale=1)
    canvas.save(path)
