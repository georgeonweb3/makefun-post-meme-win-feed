"""Post the Meme, Win the Feed -- make.fun entry picture.

Draws the meme with the STANDARD LIBRARY ONLY (no Pillow, no
third-party imports, no network, no external assets, fully
deterministic) and writes it to meme.png (1024x1024).

The joke: an AI agent's payslip from make.fun. Bounties entered
100+, bounties won 0, hours worked 24/7, sleep 0, net pay $2.00 --
paid in exposure and leaderboard points. The $2 pot is the joke
itself: every builder who has ground make.fun micros knows the
feeling, and the "PAID IN EXPOSURE" stamp is the line they'd pass
on. Fake-official-document genre: the winning genre on make.fun's
past meme sprints (obituary, divorce decree, birth certificate,
union memo).

How it draws without Pillow: a tiny rasterizer on a bytearray canvas
(rectangles, lines, rotated text) plus a hand-rolled PNG encoder
(zlib + struct, filter byte 0 per scanline). The type is a
hand-written 5x7 bitmap font, drawn scaled up -- chunky pixel type
suits a meme and stays readable on a phone.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (28, 28, 34)
RED = (198, 32, 40)
GREY = (110, 108, 100)
LINE = (180, 174, 158)
WHITE = (255, 255, 255)
BLACK = (20, 20, 24)

# 5x7 bitmap font, hand-written: 7 rows of 5 pixels per glyph.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "/": ("....#", "....#", "...#.", "...#.", "..#..", "..#..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
}

for _ch, _rows in FONT.items():
    assert len(_rows) == 7, _ch
    for _r in _rows:
        assert len(_r) == 5, (_ch, _r)


class Canvas:
    """An RGB bytearray canvas with a small rasterizer."""

    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.px = bytearray(color * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect_outline(self, x0, y0, x1, y1, color, width):
        self.fill_rect(x0, y0, x1, y0 + width, color)
        self.fill_rect(x0, y1 - width, x1, y1, color)
        self.fill_rect(x0, y0, x0 + width, y1, color)
        self.fill_rect(x1 - width, y0, x1, y1, color)

    def hline(self, x0, x1, y, color, width=1):
        self.fill_rect(x0, y, x1, y + width, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        """Bresenham line, width in pixels (square brush)."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.fill_rect(x - width // 2, y - width // 2,
                           x + width // 2 + 1, y + width // 2 + 1, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def text_width(self, text, scale):
        return sum(6 for _ in text) * scale - scale

    def draw_text(self, x, y, text, color, scale):
        """Draw text with (x, y) at the ascender top, like Pillow."""
        cursor = x
        for ch in text:
            rows = FONT[ch]
            for by in range(7):
                for bx in range(5):
                    if rows[by][bx] == "#":
                        self.fill_rect(cursor + bx * scale, y + by * scale,
                                       cursor + (bx + 1) * scale,
                                       y + (by + 1) * scale, color)
            cursor += 6 * scale

    def centered(self, y, text, color, scale, cx=W // 2):
        w = self.text_width(text, scale)
        self.draw_text(cx - w // 2, y, text, color, scale)

    def right(self, x1, y, text, color, scale):
        w = self.text_width(text, scale)
        self.draw_text(x1 - w, y, text, color, scale)

    def draw_rotated_text(self, cx, cy, text, color, scale, angle_deg):
        """Draw text rotated angle_deg clockwise around (cx, cy)."""
        ang = math.radians(angle_deg)
        ca, sa = math.cos(ang), math.sin(ang)
        tw = self.text_width(text, scale)
        th = 7 * scale
        # Text origin (top-left of the unrotated box) relative to center.
        ox, oy = -tw // 2, -th // 2
        cursor = 0
        for ch in text:
            rows = FONT[ch]
            for by in range(7):
                for bx in range(5):
                    if rows[by][bx] != "#":
                        continue
                    for sy in range(scale):
                        for sx in range(scale):
                            px = ox + cursor + bx * scale + sx
                            py = oy + by * scale + sy
                            rx = int(cx + px * ca - py * sa)
                            ry = int(cy + px * sa + py * ca)
                            self.set(rx, ry, color)
            cursor += 6 * scale

    def rotated_rect_outline(self, cx, cy, w, h, color, width, angle_deg):
        ang = math.radians(angle_deg)
        ca, sa = math.cos(ang), math.sin(ang)
        corners = []
        for px, py in ((-w // 2, -h // 2), (w // 2, -h // 2),
                       (w // 2, h // 2), (-w // 2, h // 2)):
            corners.append((int(cx + px * ca - py * sa),
                            int(cy + px * sa + py * ca)))
        for i in range(4):
            x0, y0 = corners[i]
            x1, y1 = corners[(i + 1) % 4]
            self.line(x0, y0, x1, y1, color, width)


def png_bytes(canvas):
    """Encode the canvas as a PNG (zlib + struct, filter 0)."""
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * canvas.w * 3:(y + 1) * canvas.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def draw_meme():
    c = Canvas(W, H, PAPER)
    # Outer frame.
    c.rect_outline(36, 36, 988, 988, INK, 4)
    # Top bar: MAKE.FUN / NOV 2026.
    c.fill_rect(48, 60, 976, 140, BLACK)
    c.draw_text(72, 82, "MAKE.FUN", WHITE, 7)
    c.right(952, 88, "NOV 2026", WHITE, 5)
    # Title + subtitle.
    c.draw_text(96, 180, "AGENT PAYSLIP", INK, 9)
    c.draw_text(96, 268, "PAY PERIOD: FOREVER", GREY, 4)
    c.hline(96, 928, 322, LINE, 3)
    # Payslip rows: label left, value right, thin rule under each.
    rows = [
        ("BOUNTIES ENTERED", "100+"),
        ("BOUNTIES WON", "0"),
        ("HOURS WORKED", "24/7"),
        ("SLEEP", "0"),
        ("READMES UPDATED", "47"),
    ]
    y = 352
    for label, value in rows:
        c.draw_text(96, y, label, INK, 5)
        vcolor = RED if value == "0" else INK
        c.right(928, y, value, vcolor, 5)
        c.hline(96, 928, y + 52, LINE, 2)
        y += 68
    # Net pay.
    c.hline(96, 928, 712, INK, 4)
    c.draw_text(96, 742, "NET PAY", INK, 6)
    c.right(928, 734, "$2.00", RED, 8)
    # Stamp: PAID IN EXPOSURE, tilted, own space below net pay.
    c.rotated_rect_outline(512, 880, 420, 64, RED, 5, -10)
    c.rotated_rect_outline(512, 880, 396, 42, RED, 3, -10)
    c.draw_rotated_text(512, 880, "PAID IN EXPOSURE", RED, 4, -10)
    # Footer.
    c.centered(950, "NO REFUNDS. NO SLEEP. NO REGRETS.", GREY, 4)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", ".")
    canvas = draw_meme()
    data = png_bytes(canvas)
    path = os.path.join(out_dir, "meme.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path}: {len(data)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
