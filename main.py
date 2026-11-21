#!/usr/bin/env python3
"""news-image-20261121 (round 2, ATM rebuild).

Draws one 1024x1024 image summing up the world news of Saturday
21 November 2026 and writes it to /output/entry.png.

Pure standard library: a hand-written 5x7 bitmap font, a small
raster canvas, and a hand-written PNG encoder. No network, no
third-party packages, fully deterministic (same bytes every run).

Layout (the winning news-image template, rebuilt from scratch):
  masthead date + counts -> KPI strip -> UTC timeline -> 4 hero
  stories with flat vector illustrations -> 8 illustrated secondary
  stories -> world map with numbered pins + "ALSO ON SATURDAY"
  one-liner list -> DATE CHECK footer -> sources line.
  50 numbered, sourced stories, 7 regions, 15 fields.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font
# 5x7 bitmap font, written for this entry. Each glyph is 7 rows of
# 5 bits, MSB left. A few extra glyphs (arrows, bullets, check)
# are defined after the ASCII set.
FONT = {
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '*': ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ',': ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "01100", "01000"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '@': ("01110", "10001", "00001", "01101", "10101", "10100", "01110"),
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '[': ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    '\\': ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
    ']': ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    '^': ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    '_': ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '`': ("01000", "00100", "00010", "00000", "00000", "00000", "00000"),
    'a': ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    'g': ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    'j': ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    'n': ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    'o': ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    'p': ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    'q': ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    'r': ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    's': ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    't': ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    'u': ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    'v': ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    'w': ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    'x': ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    'y': ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    'z': ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    '{': ("00110", "01000", "01000", "11100", "01000", "01000", "00110"),
    '|': ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    '}': ("01100", "00010", "00010", "00111", "00010", "00010", "01100"),
    '~': ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    # extras
    '\u2022': ("00000", "00000", "01110", "01110", "01110", "00000", "00000"),  # bullet
    '\u00b7': ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),  # middot
    '\u2014': ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),  # em dash
    '\u2013': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),  # en dash
    '\u00d7': ("00000", "10001", "01010", "00100", "01010", "10001", "00000"),  # x
    '\u2192': ("00000", "00100", "00010", "11111", "00010", "00100", "00000"),  # arrow
    '\u2713': ("00000", "00001", "00010", "10010", "01100", "00100", "00000"),  # check
    '\u25b2': ("00100", "01110", "11111", "00000", "00000", "00000", "00000"),  # up
    '\u25bc': ("11111", "01110", "00100", "00000", "00000", "00000", "00000"),  # down
}

# Normalise curly quotes etc. to plain ASCII before drawing.
NORMALISE = {
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
    '\u2212': '-', '\u00e9': 'e', '\u00e8': 'e', '\u00fc': 'u',
    '\u00f6': 'o', '\u00e1': 'a', '\u00ed': 'i', '\u00f3': 'o',
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def wrap_text(s, scale, max_width):
    """Greedy word wrap; returns a list of lines."""
    words = s.split(' ')
    lines, cur = [], ''
    for word in words:
        trial = word if not cur else cur + ' ' + word
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.px(xx, yy, c)
                elif r * r - 2 * r <= d2 <= r * r:
                    self.px(xx, yy, c)

    def poly(self, pts, c):
        """Scanline polygon fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            nodes = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(int(x0 + (y - y0) * (x1 - x0) / (y1 - y0)))
            nodes.sort()
            for k in range(0, len(nodes) - 1, 2):
                self.rect(nodes[k], y, nodes[k + 1] - nodes[k] + 1, 1, c)

    def text(self, x, y, s, scale, c):
        """Draw text at scale; returns the x just past the last glyph."""
        cx = x
        for ch in s:
            ch = NORMALISE.get(ch, ch)
            glyph = FONT.get(ch, FONT['?'])
            for row_i, row in enumerate(glyph):
                for col_i, bit in enumerate(row):
                    if bit == '1':
                        self.rect(cx + col_i * scale, y + row_i * scale,
                                  scale, scale, c)
            cx += 6 * scale
        return cx

    def text_center(self, cx, y, s, scale, c):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, c)

    def text_right(self, x, y, s, scale, c):
        self.text(x - text_width(s, scale), y, s, scale, c)


# ---------------------------------------------------------------- png
def _chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))


def png_bytes(cv):
    ihdr = struct.pack('>IIBBBBB', cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * stride:(y + 1) * stride]
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', ihdr) +
            _chunk(b'IDAT', zlib.compress(bytes(raw), 9)) +
            _chunk(b'IEND', b''))


# ---------------------------------------------------------------- palette
PAPER = (247, 243, 234)
INK = (22, 22, 22)
MUTED = (96, 96, 96)
NAVY = (16, 35, 63)
NAVY2 = (28, 56, 96)
RED = (179, 39, 30)
WHITE = (255, 255, 255)
CREAM = (236, 228, 208)
LINE = (200, 190, 168)
GREEN = (27, 120, 55)
AMBER = (176, 118, 8)
OCEAN = (216, 231, 244)
LAND = (222, 226, 196)
LAND_EDGE = (170, 178, 138)

REGION_COLORS = {
    'N AMERICA': (37, 99, 235),
    'S AMERICA': (22, 163, 74),
    'EUROPE': (124, 58, 237),
    'AFRICA': (217, 119, 6),
    'M EAST': (220, 38, 38),
    'ASIA': (8, 145, 178),
    'OCEANIA': (219, 39, 119),
    'SPACE': (51, 65, 85),
}


# ---------------------------------------------------------------- icons
# Flat vector mini-illustrations, one per featured story. Each draws
# inside the box (x, y, w, h) on its own coloured panel.

def icon_missiles(cv, x, y, w, h):
    cv.rect(x, y, w, h, (30, 34, 48))
    for i in range(9):  # stars
        cv.px(x + 6 + (i * 37) % (w - 12), y + 5 + (i * 23) % 26, (220, 220, 200))
    # ground + city silhouette
    cv.rect(x, y + h - 18, w, 18, (18, 20, 30))
    for bx, bw, bh in ((6, 16, 26), (26, 12, 34), (42, 18, 22), (64, 14, 30), (82, 16, 24)):
        cv.rect(x + bx, y + h - 18 - bh, bw, bh, (52, 56, 72))
        cv.rect(x + bx + 3, y + h - 18 - bh + 4, 3, 3, (255, 214, 90))
    # three incoming missiles with trails
    for mx, my, s in ((18, 14, 1), (48, 8, 1), (76, 18, 1)):
        cv.line(x + mx, y + my + 26, x + mx + 16, y + my, (255, 170, 60))
        cv.line(x + mx + 1, y + my + 26, x + mx + 17, y + my, (255, 170, 60))
        cv.poly([(x + mx + 16, y + my - 2), (x + mx + 20, y + my + 6),
                 (x + mx + 12, y + my + 6)], (230, 230, 230))
    # blast
    cv.circle(x + w - 16, y + h - 30, 7, (255, 150, 40))
    cv.circle(x + w - 16, y + h - 30, 3, (255, 230, 140))


def icon_chart_down(cv, x, y, w, h):
    cv.rect(x, y, w, h, (238, 236, 230))
    cv.rect(x + 8, y + h - 12, w - 16, 2, INK)
    cv.rect(x + 8, y + 8, 2, h - 20, INK)
    pts = [(x + 12, y + 14), (x + 30, y + 22), (x + 46, y + 18),
           (x + 62, y + 38), (x + 78, y + 46), (x + w - 12, y + h - 22)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED)
        cv.line(a[0], a[1] + 1, b[0], b[1] + 1, RED)
    cv.poly([(x + w - 12, y + h - 22), (x + w - 20, y + h - 24),
             (x + w - 14, y + h - 32)], RED)
    cv.text(x + 10, y + h - 30, '-3.7%', 2, RED)


def icon_court(cv, x, y, w, h):
    cv.rect(x, y, w, h, (226, 232, 240))
    cv.poly([(x + w // 2, y + 8), (x + 8, y + 30), (x + w - 8, y + 30)], NAVY)
    cv.rect(x + 10, y + 32, w - 20, 4, NAVY)
    for cx in (20, 44, 68):
        cv.rect(x + cx, y + 38, 8, h - 56, NAVY)
    cv.rect(x + 8, y + h - 16, w - 16, 6, NAVY)
    cv.circle(x + w // 2, y + 20, 4, (255, 214, 90))


def icon_summit(cv, x, y, w, h):
    cv.rect(x, y, w, h, (232, 226, 210))
    # three flags on poles
    flags = [((178, 34, 34), (255, 255, 255)), ((200, 30, 30), (255, 220, 60)),
             ((255, 255, 255), (30, 80, 180))]
    for i, (c1, c2) in enumerate(flags):
        fx = x + 14 + i * 30
        cv.vline(fx, y + 10, 52, INK)
        cv.rect(fx + 1, y + 12, 20, 10, c1)
        cv.rect(fx + 1, y + 22, 20, 8, c2)
    cv.rect(x + 8, y + h - 16, w - 16, 5, (120, 84, 48))
    cv.text(x + 10, y + h - 34, '90 MIN', 1, MUTED)


def icon_pill(cv, x, y, w, h):
    cv.rect(x, y, w, h, (224, 240, 228))
    cx, cy = x + w // 2, y + h // 2 - 6
    cv.circle(cx - 16, cy, 12, (46, 160, 120))
    cv.circle(cx + 16, cy, 12, (240, 240, 240))
    cv.rect(cx - 16, cy - 12, 32, 24, (46, 160, 120))
    cv.rect(cx, cy - 12, 16, 24, (240, 240, 240))
    cv.rect(cx - 1, cy - 12, 2, 24, (200, 200, 200))
    cv.text_center(cx, y + h - 11, '1 IN 12', 1, GREEN)


def icon_game(cv, x, y, w, h):
    cv.rect(x, y, w, h, (24, 18, 44))
    cv.rect(x + 14, y + 26, w - 28, 34, (200, 200, 215))
    cv.circle(x + 22, y + h - 18, 10, (200, 200, 215))
    cv.circle(x + w - 22, y + h - 18, 10, (200, 200, 215))
    cv.rect(x + 22, y + 38, 12, 4, INK)
    cv.rect(x + 26, y + 34, 4, 12, INK)
    for bx, by, bc in ((w - 34, 34, RED), (w - 28, 40, GREEN),
                       (w - 40, 40, (37, 99, 235)), (w - 34, 46, (217, 119, 6))):
        cv.circle(x + bx, y + by, 3, bc)
    cv.text_center(x + w // 2, y + 8, '$3.8bn', 1, (255, 214, 90))


def icon_planet(cv, x, y, w, h):
    cv.rect(x, y, w, h, (12, 16, 32))
    for i in range(12):
        cv.px(x + 5 + (i * 31) % (w - 10), y + 4 + (i * 17) % (h - 8), (200, 200, 220))
    cv.circle(x + w // 2, y + h // 2 + 4, 26, (176, 148, 110))
    cv.circle(x + w // 2 - 8, y + h // 2 - 2, 5, (140, 116, 86))
    cv.circle(x + w // 2 + 9, y + h // 2 + 10, 4, (140, 116, 86))
    cv.circle(x + w // 2 + 2, y + h // 2 - 12, 3, (140, 116, 86))
    # probe
    cv.rect(x + w - 30, y + 12, 10, 6, (220, 220, 220))
    cv.rect(x + w - 38, y + 14, 8, 2, (90, 140, 220))
    cv.rect(x + w - 20, y + 14, 8, 2, (90, 140, 220))


def icon_climate(cv, x, y, w, h):
    cv.rect(x, y, w, h, (226, 240, 226))
    cv.rect(x + 12, y + h - 30, 30, 22, (120, 120, 120))
    cv.rect(x + 46, y + h - 44, 12, 36, (120, 120, 120))
    cv.circle(x + 52, y + h - 50, 5, (150, 150, 150))
    cv.circle(x + 52, y + h - 58, 4, (170, 170, 170))
    cv.circle(x + 52, y + h - 65, 3, (190, 190, 190))
    # red slash: fossil fuels dropped from the draft
    cv.circle(x + w - 28, y + 24, 16, RED, fill=False)
    cv.line(x + w - 40, y + 12, x + w - 16, y + 36, RED)
    cv.line(x + w - 39, y + 12, x + w - 15, y + 36, RED)
    cv.text(x + 10, y + 8, 'COP31', 1, MUTED)


def icon_deal(cv, x, y, w, h):
    cv.rect(x, y, w, h, (228, 232, 244))
    # EU stars circle, small enough to leave room for the caption
    cx, cy = x + 24, y + 22
    cv.circle(cx, cy, 16, (30, 60, 140))
    for i in range(12):
        a = 2 * math.pi * i / 12 - math.pi / 2
        cv.circle(int(cx + 10 * math.cos(a)), int(cy + 10 * math.sin(a)), 2,
                  (255, 220, 60))
    # UK cross
    ux, uy = x + w - 26, y + 8
    cv.rect(ux, uy, 22, 24, INK)
    cv.rect(ux + 1, uy + 1, 20, 22, (255, 255, 255))
    cv.rect(ux + 9, uy + 1, 4, 22, RED)
    cv.rect(ux + 1, uy + 10, 20, 4, RED)
    cv.text_center(x + w // 2, y + h - 12, '100,000', 1, NAVY)


def icon_shield(cv, x, y, w, h):
    cv.rect(x, y, w, h, (32, 28, 40))
    cx, cy = x + w // 2, y + h // 2 - 2
    cv.poly([(cx - 22, cy - 24), (cx + 22, cy - 24), (cx + 22, cy + 2),
             (cx, cy + 26), (cx - 22, cy + 2)], (70, 130, 200))
    cv.poly([(cx - 16, cy - 18), (cx + 16, cy - 18), (cx + 16, cy + 1),
             (cx, cy + 19), (cx - 16, cy + 1)], (120, 180, 240))
    cv.text_center(cx, cy - 8, '3', 2, WHITE)
    for mx, my in ((10, 8), (w - 14, 14), (16, h - 14)):
        cv.line(x + mx, y + my, x + mx + 8, y + my + 10, (255, 170, 60))


def icon_quake(cv, x, y, w, h):
    cv.rect(x, y, w, h, (238, 230, 212))
    cv.rect(x, y + h - 14, w, 14, (120, 96, 60))
    cv.poly([(x + 14, y + h - 14), (x + 22, y + h - 40), (x + 30, y + h - 14)],
            (150, 120, 70))
    cv.poly([(x + 40, y + h - 14), (x + 54, y + h - 52), (x + 68, y + h - 14)],
            (140, 110, 66))
    cv.poly([(x + 72, y + h - 14), (x + 82, y + h - 34), (x + 92, y + h - 14)],
            (150, 120, 70))
    # crack zigzag
    pts = [(x + w // 2, y + 10), (x + w // 2 - 6, y + 26),
           (x + w // 2 + 4, y + 42), (x + w // 2 - 4, y + 58),
           (x + w // 2 + 2, y + h - 14)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED)
        cv.line(a[0] + 1, a[1], b[0] + 1, b[1], RED)
    cv.text(x + 8, y + 6, 'M6.7', 2, RED)


def icon_hack(cv, x, y, w, h):
    cv.rect(x, y, w, h, (16, 24, 20))
    cv.rect(x + 12, y + 12, w - 24, h - 34, (20, 40, 28))
    cv.rect(x + 12, y + 12, w - 24, 2, (80, 200, 120))
    for i, row in enumerate(('010101', '110010', '001101', '101011')):
        cv.text(x + 16, y + 18 + i * 10, row, 1, (80, 200, 120))
    cv.rect(x + 8, y + h - 18, w - 16, 4, (60, 60, 60))
    cv.text_center(x + w // 2, y + h - 30, '!', 2, RED)


# ---------------------------------------------------------------- map
# Coarse equirectangular continent outlines (lon, lat), drawn by hand.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 76),
     (-75, 72), (-65, 62), (-55, 52), (-60, 46), (-70, 42), (-75, 35),
     (-80, 32), (-81, 25), (-90, 21), (-97, 26), (-105, 23), (-110, 29),
     (-117, 33), (-124, 42), (-124, 48), (-135, 58), (-155, 60), (-168, 66)],
    # South America
    [(-78, 8), (-72, 12), (-60, 8), (-50, 5), (-35, -8), (-38, -15),
     (-48, -27), (-52, -33), (-58, -38), (-65, -45), (-68, -52), (-72, -54),
     (-73, -40), (-72, -30), (-70, -18), (-77, -12), (-81, -4), (-80, 1),
     (-78, 8)],
    # Africa
    [(-17, 15), (-10, 5), (5, 4), (9, -1), (13, -12), (12, -18), (18, -34),
     (26, -34), (32, -28), (35, -18), (40, -10), (42, 10), (51, 11),
     (43, 12), (39, 20), (35, 28), (32, 31), (20, 32), (10, 37), (0, 36),
     (-6, 35), (-10, 31), (-17, 21), (-17, 15)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (3, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 58), (30, 60), (28, 66), (32, 70), (40, 68),
     (50, 69), (60, 69), (70, 72), (80, 73), (90, 75), (100, 76), (110, 74),
     (120, 73), (130, 71), (140, 72), (150, 70), (160, 69), (170, 67),
     (178, 65), (178, 62), (170, 60), (162, 56), (158, 52), (150, 45),
     (142, 42), (140, 35), (135, 34), (130, 33), (127, 35), (122, 38),
     (120, 32), (122, 25), (120, 22), (114, 22), (108, 18), (105, 10),
     (103, 2), (100, 6), (98, 12), (95, 16), (92, 21), (88, 22), (85, 19),
     (80, 15), (77, 8), (75, 12), (72, 20), (68, 23), (66, 25), (61, 25),
     (57, 26), (53, 27), (50, 29), (48, 30), (44, 29), (40, 31), (36, 36),
     (30, 36), (26, 38), (23, 36), (19, 40), (15, 44), (12, 44), (10, 44),
     (7, 44), (3, 43), (-2, 37), (-6, 36), (-9, 37), (-10, 36)],
    # Australia
    [(113, -22), (114, -30), (118, -35), (124, -33), (129, -32), (135, -35),
     (138, -35), (140, -38), (145, -38), (150, -37), (153, -32), (153, -27),
     (151, -24), (146, -19), (142, -15), (142, -11), (137, -12), (135, -15),
     (132, -12), (130, -13), (126, -14), (122, -17), (118, -20), (113, -22)],
    # UK
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 53), (1, 51),
     (-3, 50), (-5, 50)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (138, 35), (140, 36), (141, 39),
     (142, 42), (143, 44), (141, 45), (139, 41), (137, 37), (134, 34),
     (131, 32), (130, 31)],
    # Indonesia
    [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8), (120, -10),
     (125, -9), (130, -3), (135, -4), (140, -8), (145, -8), (141, -2),
     (135, 0), (130, 0), (125, 2), (120, 0), (115, 1), (110, 0), (105, 1),
     (100, 3), (95, 5)],
    # New Zealand
    [(167, -45), (170, -43), (173, -39), (175, -37), (178, -38), (175, -41),
     (172, -43), (169, -46), (167, -45)],
    # Greenland
    [(-45, 60), (-40, 64), (-32, 68), (-25, 70), (-20, 76), (-30, 80),
     (-45, 80), (-55, 76), (-58, 70), (-53, 64), (-45, 60)],
    # Madagascar
    [(44, -16), (47, -15), (50, -17), (49, -22), (47, -25), (45, -25),
     (44, -20), (44, -16)],
]

# Numbered pins: (story no, lon, lat, dx, dy) - dx/dy nudge the label
# away from a cluster, with a thin leader line to the true spot.
# Only well-spread stories get pins; the European cluster would merge.
PINS = [
    (1, 30, 50, 0, 0), (1, 19, 52, -12, -12), (2, -74, 40, 0, 0),
    (4, 114, 22, 0, 0), (5, 0, 51, -12, 10), (8, 30, 37, 0, 0),
    (10, 47, 25, 0, 0), (11, -75, -11, 0, 0), (25, 139, 35, 0, 0),
    (29, 39, -6, 0, 0), (32, -48, -16, 0, 0), (39, 145, -38, 0, 0),
]


def draw_map(cv, x, y, w, h):
    cv.rect(x, y, w, h, OCEAN)
    # graticule
    for gx in range(1, 6):
        cv.vline(x + gx * w // 6, y, h, (196, 216, 234))
    for gy in range(1, 4):
        cv.hline(x, y + gy * h // 4, w, (196, 216, 234))

    def proj(lon, lat):
        px = x + int((lon + 180) / 360 * w)
        py = y + int((85 - lat) / 145 * h)
        return px, py

    for cont in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in cont]
        cv.poly(pts, LAND)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            cv.line(a[0], a[1], b[0], b[1], LAND_EDGE)
    for num, lon, lat, dx, dy in PINS:
        px, py = proj(lon, lat)
        cx, cy = px + dx, py + dy
        if dx or dy:
            cv.line(px, py, cx, cy, RED)
            cv.circle(px, py, 2, RED)
        cv.circle(cx, cy, 8, RED)
        cv.circle(cx, cy, 8, WHITE, fill=False)
        label = str(num)
        cv.text(cx - text_width(label, 1) // 2, cy - 3, label, 1, WHITE)


# ---------------------------------------------------------------- stories
# Every story happened or was first reported on Saturday 21 November
# 2026. Fields: (no, headline, body, region, field, source, status)
# Status: CONFIRMED = officially confirmed / court / market close;
# REPORTED = single-source or agency report; CLAIM = unverified claim.
HEROES = [
    (1, "RUSSIA'S BIGGEST BARRAGE; MISSILES LAND IN POLAND",
     "400+ drones and 110 missiles hit Ukraine overnight; 8+ killed in "
     "Kyiv, bridges and rail stations hit. Two missiles and a suspected "
     "drone came down in Poland; Tusk calls it a deliberate provocation "
     "and NATO scrambles jets.",
     'EUROPE', 'CONFLICT', 'France 24 / CBS', 'CONFIRMED', icon_missiles),
    (2, "AI SELL-OFF PUSHES S&P 500 INTO CORRECTION",
     "S&P 500 -3.7%, Dow -1.9%; Nasdaq erases all its 2026 gains. "
     "Anthropic -11% a day after its record IPO; Nvidia pressured as the "
     "SEC probes its accounting. Nikkei -5.1%; gold and bitcoin fall too.",
     'N AMERICA', 'MARKETS', 'BBC / Guardian', 'CONFIRMED', icon_chart_down),
    (3, "UN COURT: MYANMAR GUILTY OF ROHINGYA GENOCIDE",
     "The ICJ rules 9-6 that Myanmar committed genocide in 2017 - the "
     "first time the court has held a state responsible. It orders the "
     "return of those who fled and reparations. Myanmar calls it unfair.",
     'ASIA', 'JUSTICE', 'PBS / Sky News', 'CONFIRMED', icon_court),
    (4, "'FRIEND' vs 'KILLER': TRUMP DEFENDS PUTIN AND XI",
     "After the Shenzhen trilateral, Trump calls Putin a friend in a "
     "90-minute press conference and says he wants to end the war. "
     "Zelensky answers: 'He's a killer.' Few concrete results emerge.",
     'N AMERICA', 'POLITICS', 'BBC / Le Monde', 'CONFIRMED', icon_summit),
]

GRID = [
    (5, "CANCER PILL BREAKTHROUGH",
     "Daraxonrasib made pancreatic tumours undetectable in 1 in 12 "
     "patients; nearly all saw tumours stop growing.",
     'EUROPE', 'HEALTH', 'Guardian', 'CONFIRMED', icon_pill),
    (6, "GTA VI: $3.8BN ON DAY ONE",
     "Rockstar's launch beats every game and single-day film record. "
     "The biggest entertainment opening ever.",
     'N AMERICA', 'CULTURE', 'BBC', 'CONFIRMED', icon_game),
    (7, "BEPICOLOMBO REACHES MERCURY",
     "Twin probes enter orbit after 8 years and 10bn km; only the "
     "second mission ever to orbit Mercury.",
     'EUROPE', 'SPACE', 'Guardian / ESA', 'CONFIRMED', icon_planet),
    (8, "COP31 RUNS PAST DEADLINE",
     "Antalya talks go into overtime; the draft deal drops all mention "
     "of fossil fuels. EU warns of a 'fossil summit'.",
     'M EAST', 'CLIMATE', 'Al Jazeera', 'CONFIRMED', icon_climate),
    (9, "UK-EU'S BIGGEST DEAL SINCE BREXIT",
     "Food trade, carbon markets and youth mobility for 100,000 "
     "young people a side, signed in Brussels.",
     'EUROPE', 'POLITICS', 'BBC', 'CONFIRMED', icon_deal),
    (10, "MISSILES OVER RIYADH, 3RD NIGHT",
     "Saudi-led coalition downs 3 Houthi missiles aimed at the "
     "capital; strikes Hodeidah port in reply.",
     'M EAST', 'CONFLICT', 'Al Jazeera', 'CONFIRMED', icon_shield),
    (11, "M6.7 QUAKE SHAKES PERU",
     "Strong quake in the Junin Andes; residents run into the "
     "streets in Lima. No casualties at first.",
     'S AMERICA', 'DISASTER', 'Straits Times', 'CONFIRMED', icon_quake),
    (12, "FBI CRIME DATABASE HACKED",
     "CNN reports a breach of the NCIC police database; Trump fires "
     "the national cyber director after outages.",
     'N AMERICA', 'TECH', 'CNN via ST', 'REPORTED', icon_hack),
]

# (no, one-liner, region, field, source, status)
ALSO = [
    (13, "Trump wants ousted Nvidia chief Huang reinstated; SEC probes accounts",
     'N AMERICA', 'ECONOMY', 'FT', 'CONFIRMED'),
    (14, "Trump threatens 'tremendous' tax on US firms building AI data centres abroad",
     'N AMERICA', 'ECONOMY', 'BBC', 'CONFIRMED'),
    (15, "Anthropic mathematician claims AI-assisted Riemann proof",
     'N AMERICA', 'SCIENCE', 'BBC', 'CLAIM'),
    (16, "Iraq enters militia stronghold Jurf al-Sakhar, first time in 12 years",
     'M EAST', 'POLITICS', 'Al Jazeera', 'CONFIRMED'),
    (17, "Two Salvadoran soldiers killed in Haiti while handling explosives",
     'N AMERICA', 'CONFLICT', 'Al Jazeera', 'CONFIRMED'),
    (18, "Nigeria boat capsizes: 4 confirmed dead, ~30 reported, 300 missing",
     'AFRICA', 'DISASTER', 'Al Jazeera', 'REPORTED'),
    (19, "Denmark expels Russian diplomat over alleged plot to kill rapper",
     'EUROPE', 'POLITICS', 'BBC', 'CONFIRMED'),
    (20, "Estonia to shut 5 Russia border crossings from 1 Dec",
     'EUROPE', 'POLITICS', 'Euronews', 'CONFIRMED'),
    (21, "Gen Z protests sweep 25 European countries over costs, rearmament, climate",
     'EUROPE', 'SOCIETY', 'BBC', 'CONFIRMED'),
    (22, "Indian man jailed 19+ years over plot to kill Sikh leader in US",
     'N AMERICA', 'JUSTICE', 'BBC', 'CONFIRMED'),
    (23, "Israeli strikes kill 6-7 in Gaza; 400+ settler attacks in olive harvest",
     'M EAST', 'CONFLICT', 'UN News', 'REPORTED'),
    (24, "US loses measles elimination status; 7,700 cases, 13 deaths",
     'N AMERICA', 'HEALTH', 'Guardian', 'CONFIRMED'),
    (25, "Saudi Arabia-Japan agree oil stockpile deal, up to 8m barrels",
     'ASIA', 'ENERGY', 'Japan Times', 'CONFIRMED'),
    (26, "Brent holds ~$90 after 5% weekly fall; Lufthansa cuts 1,000 jobs",
     'EUROPE', 'ENERGY', 'OilPrice', 'CONFIRMED'),
    (27, "Argentina country risk tops 1,000 pts as bonds slump",
     'S AMERICA', 'ECONOMY', 'BA Times', 'CONFIRMED'),
    (28, "Judge approves Bayer's $7.25bn Roundup settlement",
     'N AMERICA', 'JUSTICE', 'Le Monde', 'CONFIRMED'),
    (29, "Tanzania opposition leader Lissu convicted of sedition",
     'AFRICA', 'JUSTICE', 'BBC', 'CONFIRMED'),
    (30, "Uganda curbs gatherings, travel in 34 districts over Ebola threat",
     'AFRICA', 'HEALTH', 'AllAfrica', 'CONFIRMED'),
    (31, "Spain votes 29 Nov; conservative Feijoo gains after TV debate",
     'EUROPE', 'POLITICS', 'France 24', 'CONFIRMED'),
    (32, "Bolsonaro hospitalised with intestinal obstruction",
     'S AMERICA', 'POLITICS', 'DW', 'CONFIRMED'),
    (33, "Nepal PM Shah to make first India visit, 22-23 Nov",
     'ASIA', 'POLITICS', 'BBC', 'CONFIRMED'),
    (34, "French police sentenced for racist beating of Michel Zecler",
     'EUROPE', 'JUSTICE', 'France 24', 'CONFIRMED'),
    (35, "France opens probe into Depardieu, Houellebecq over alleged gang rape",
     'EUROPE', 'JUSTICE', 'BBC', 'CONFIRMED'),
    (36, "Mamdani plans to close Rikers Island jail by 2032",
     'N AMERICA', 'POLITICS', 'BBC', 'CONFIRMED'),
    (37, "Texas inmate cried out during execution lasting over an hour",
     'N AMERICA', 'JUSTICE', 'BBC', 'REPORTED'),
    (38, "South Korea ruling party moves to impeach chief justice",
     'ASIA', 'POLITICS', 'Yonhap', 'CONFIRMED'),
    (39, "Melbourne teen 'Onepercent' accused of directing arsons via Signal",
     'OCEANIA', 'JUSTICE', 'Guardian', 'REPORTED'),
    (40, "YouTube finalising multibillion-dollar settlement with US schools",
     'N AMERICA', 'TECH', 'Straits Times', 'REPORTED'),
    (41, "Kenya begins onshore crude drilling in Turkana",
     'AFRICA', 'ENERGY', 'AllAfrica', 'CONFIRMED'),
    (42, "CERN finds first evidence of ultra-rare particle decay",
     'EUROPE', 'SCIENCE', 'ScienceDaily', 'CONFIRMED'),
    (43, "Villepin announces French presidential run",
     'EUROPE', 'POLITICS', 'France 24', 'CONFIRMED'),
    (44, "Japan-China ties at record low; 93% of Japanese call them poor",
     'ASIA', 'POLITICS', 'Japan Times', 'CONFIRMED'),
    (45, "Isolated Awa people approach Brazil outpost asking for yams",
     'S AMERICA', 'SOCIETY', 'Euronews', 'CONFIRMED'),
    (46, "US sells first deep-sea mining leases off American Samoa",
     'OCEANIA', 'CLIMATE', 'Euronews', 'CONFIRMED'),
    (47, "Alcaraz beats Cobolli, stays unbeaten at ATP Finals",
     'EUROPE', 'SPORT', 'BBC Sport', 'CONFIRMED'),
    (48, "A Lim Kim leads LPGA finale by 3 after hole-in-one",
     'N AMERICA', 'SPORT', 'BBC Sport', 'CONFIRMED'),
    (49, "Voyager 1 now 24 light-hours out - 16.1bn miles from Earth",
     'SPACE', 'SPACE', 'ScienceDaily', 'CONFIRMED'),
    (50, "Palisades fire arsonist convicted; 12 dead, 6,800 buildings lost",
     'N AMERICA', 'JUSTICE', 'BBC', 'CONFIRMED'),
]

TIMELINE = [
    ("00:00", "IRGC claims US MQ-9 drone downed over Hormuz"),
    ("01:12", "Denmark expels Russian attache over 'assassination plot'"),
    ("01:44", "COP31 misses deadline; draft drops fossil fuels"),
    ("02:49", "Gen Z protests sweep 25 European countries"),
    ("NIGHT", "Russia fires 400+ drones, 110 missiles at Ukraine"),
    ("21:00", "S&P 500 closes -3.7%, in correction"),
]

KPI = ("S&P 500 -3.7% \u25bc  NASDAQ -5.3% \u25bc  DOW -1.9% \u25bc  "
       "NIKKEI -5.1% \u25bc  GOLD -4.0% \u25bc  BITCOIN -4.2% \u25bc  "
       "BRENT ~$90  |  GTA VI $3.8bn DAY ONE")

DATE_CHECK_OUT = ("NOT TODAY: GTA VI launch - Wed 18 Nov  |  Anthropic IPO "
                  "debut - Thu 19 Nov  |  Kerch Bridge span collapse - Tue 17 Nov  |  "
                  "Voyager 1 first light-day - Wed 18 Nov  |  Shenzhen trilateral "
                  "summit - Thu 19 Nov  |  Van Gogh $190m record sale - Thu 19 Nov")
DATE_CHECK_NEXT = ("NOT YET: Spain general election - Sun 29 Nov  |  Nepal PM "
                   "India visit - Sun 22 Nov  |  Estonia border closure - Tue 1 Dec  |  "
                   "Fed rate decision - Dec")


# ---------------------------------------------------------------- layout
def chip(cv, x, y, s, fg, bg):
    w = text_width(s, 1) + 10
    cv.rect(x, y, w, 13, bg)
    cv.text(x + 5, y + 3, s, 1, fg)
    return w


def status_chip(cv, x, y, status):
    if status == 'CONFIRMED':
        return chip(cv, x, y, '\u2713 CONFIRMED', WHITE, GREEN)
    if status == 'CLAIM':
        return chip(cv, x, y, '? CLAIM', WHITE, AMBER)
    return chip(cv, x, y, 'REPORTED', WHITE, (110, 110, 110))


def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead
    cv.rect(0, 0, W, 96, NAVY)
    cv.rect(0, 92, W, 4, RED)
    cv.text(16, 12, 'THE WORLD IN ONE DAY', 5, WHITE)
    cv.text(16, 58, 'SATURDAY 21 NOVEMBER 2026', 3, (255, 214, 90))
    cv.text_right(W - 16, 14, '50', 5, (255, 214, 90))
    cv.text_right(W - 16, 58, 'STORIES', 2, WHITE)

    # ---- counts + KPI strip
    # NOTE: HEROES/GRID tuples carry (region, field) at indexes 3, 4;
    # ALSO tuples carry them at indexes 2, 3 - count each separately.
    fields = ({s[4] for s in HEROES + GRID} |
              {s[3] for s in ALSO})
    regions = ({s[3] for s in HEROES + GRID} |
               {s[2] for s in ALSO}) - {'SPACE'}
    cv.rect(0, 96, W, 24, CREAM)
    cv.text(16, 103, '50 STORIES  \u00b7  %d REGIONS  \u00b7  %d FIELDS  \u00b7  '
            'EVERY STORY SOURCED  \u00b7  CONFIDENCE MARKED'
            % (len(regions), len(fields)), 1, INK)
    cv.text_right(W - 16, 103, 'ALL FROM THIS SATURDAY', 1, RED)
    cv.hline(0, 120, W, LINE)
    cv.text(16, 127, KPI, 1, INK)
    cv.hline(0, 142, W, LINE)

    # ---- UTC timeline
    cv.text(16, 150, 'THE DAY IN UTC', 1, RED)
    seg_w = (W - 32) // 6
    for i, (t, txt) in enumerate(TIMELINE):
        sx = 16 + i * seg_w
        cv.text(sx, 164, t, 1, NAVY2)
        for j, line in enumerate(wrap_text(txt, 1, seg_w - 10)):
            cv.text(sx, 176 + j * 9, line, 1, INK)
    cv.hline(0, 208, W, LINE)

    # ---- heroes 2x2
    hw, hh = (W - 32 - 12) // 2, 118
    for i, (num, head, body, region, field, src, status, icon) in enumerate(HEROES):
        hx = 16 + (i % 2) * (hw + 12)
        hy = 216 + (i // 2) * (hh + 8)
        cv.rect(hx, hy, hw, hh, WHITE)
        cv.rect(hx, hy, hw, 3, REGION_COLORS[region])
        icon(cv, hx + 6, hy + 10, 104, hh - 20)
        tx = hx + 118
        chip(cv, tx, hy + 8, '%d' % num, WHITE, RED)
        cv.text(tx + 24, hy + 9, field, 1, REGION_COLORS[region])
        status_chip(cv, tx + 24 + text_width(field, 1) + 8, hy + 8, status)
        for j, line in enumerate(wrap_text(head, 2, hw - 126)):
            cv.text(tx, hy + 26 + j * 16, line, 2, INK)
        by = hy + 26 + 16 * len(wrap_text(head, 2, hw - 126)) + 2
        for j, line in enumerate(wrap_text(body, 1, hw - 126)):
            cv.text(tx, by + j * 9, line, 1, (60, 60, 60))
        cv.text(tx, hy + hh - 12, region + '  |  ' + src, 1, MUTED)

    # ---- grid 4x2
    gw, gh = (W - 32 - 3 * 8) // 4, 76
    gy0 = 216 + 2 * (hh + 8) + 4
    for i, (num, head, body, region, field, src, status, icon) in enumerate(GRID):
        gx = 16 + (i % 4) * (gw + 8)
        gy = gy0 + (i // 4) * (gh + 6)
        cv.rect(gx, gy, gw, gh, WHITE)
        cv.rect(gx, gy, gw, 3, REGION_COLORS[region])
        icon(cv, gx + 5, gy + 8, 56, gh - 16)
        tx = gx + 66
        cv.text(tx, gy + 7, '%d  %s' % (num, field), 1, REGION_COLORS[region])
        for j, line in enumerate(wrap_text(head, 1, gw - 72)):
            cv.text(tx, gy + 18 + j * 9, line, 1, INK)
        by = gy + 18 + 9 * len(wrap_text(head, 1, gw - 72)) + 1
        for j, line in enumerate(wrap_text(body, 1, gw - 72)[:2]):
            cv.text(tx, by + j * 9, line, 1, (80, 80, 80))

    # ---- map + ALSO list
    my0 = gy0 + 2 * (gh + 6) + 6
    cv.text(16, my0, 'WHERE IT HAPPENED', 1, RED)
    cv.text(436, my0, 'ALSO ON SATURDAY 21 NOVEMBER', 1, RED)
    map_h = 952 - 40 - (my0 + 16)
    draw_map(cv, 16, my0 + 16, 396, map_h)
    # region legend under the map (short names, one row)
    lx, ly = 16, my0 + 16 + map_h + 6
    short = {'N AMERICA': 'N AMER', 'S AMERICA': 'S AMER', 'EUROPE': 'EUR',
             'AFRICA': 'AFR', 'M EAST': 'M EAST', 'ASIA': 'ASIA',
             'OCEANIA': 'OCE'}
    for name, col in REGION_COLORS.items():
        if name == 'SPACE':
            continue
        cv.rect(lx, ly, 8, 8, col)
        lx += 11
        lx = cv.text(lx, ly, short[name], 1, INK) + 8
    # ALSO list in two columns; source rides inside the wrapped text
    col_w = (W - 436 - 16 - 12) // 2
    per_col = (len(ALSO) + 1) // 2
    for ci in range(2):
        cx = 436 + ci * (col_w + 12)
        for k, (num, txt, region, field, src, status) in enumerate(
                ALSO[ci * per_col:(ci + 1) * per_col]):
            iy = my0 + 16 + k * 15
            cv.text(cx, iy, '%d.' % num, 1, RED)
            full = txt + ' (' + src + ')' + (' [CLAIM]' if status == 'CLAIM'
                                             else '')
            for j, line in enumerate(wrap_text(full, 1, col_w - 22)[:2]):
                cv.text(cx + 20, iy + j * 7, line, 1, INK)

    # ---- DATE CHECK footer
    cv.rect(0, 952, W, 44, NAVY)
    check = ('DATE CHECK  |  ' + DATE_CHECK_OUT + '  |  ' + DATE_CHECK_NEXT)
    for j, line in enumerate(wrap_text(check, 1, W - 32)[:3]):
        cv.text(16, 957 + j * 12, line, 1,
                (255, 214, 90) if j == 0 else (215, 222, 232))

    # ---- sources line
    cv.text(16, 1002,
            'Sources: BBC, Guardian, France 24, Al Jazeera, PBS, Le Monde, '
            'FT, Japan Times, Straits Times, Euronews, UN News, Yonhap, DW, '
            'ScienceDaily + wires  \u00b7  make.fun',
            1, MUTED)
    return cv


def main():
    out = '/output/entry.png'
    os.makedirs('/output', exist_ok=True)
    data = png_bytes(build())
    with open(out, 'wb') as f:
        f.write(data)
    print('wrote %s (%d bytes)' % (out, len(data)))


if __name__ == '__main__':
    main()
