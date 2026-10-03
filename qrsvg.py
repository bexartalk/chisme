"""v49.14: a tiny QR code encoder (byte mode, error correction M, versions 1-10, up to 213 bytes) that draws an SVG.
No dependencies. Used for the desktop homepage's "open it on your phone" code (website.py /qr.svg). Follows the
QR Code spec (ISO/IEC 18004) the same way Project Nayuki's MIT-licensed qrcodegen does."""
from __future__ import annotations

# version -> (EC codewords per block, [(blocks, data codewords per block), ...]) for error correction level M
_M = {1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]), 5: (24, [(2, 43)]),
      6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]), 9: (22, [(3, 36), (2, 37)]),
      10: (26, [(4, 43), (1, 44)])}
_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
          9: [6, 26, 46], 10: [6, 28, 50]}
_MASKS = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
          lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
          lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
          lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]


def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree: int) -> list[int]:
    res = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            res[j] = _gf_mul(res[j], root)
            if j + 1 < degree:
                res[j] ^= res[j + 1]
        root = _gf_mul(root, 2)
    return res


def _rs_remainder(data: list[int], div: list[int]) -> list[int]:
    res = [0] * len(div)
    for b in data:
        f = b ^ res.pop(0)
        res.append(0)
        for i, c in enumerate(div):
            res[i] ^= _gf_mul(c, f)
    return res


def _codewords(data: bytes) -> tuple[int, list[int]]:
    for ver in range(1, 11):
        ec, groups = _M[ver]
        cap = sum(n * k for n, k in groups)
        cc_bits = 8 if ver < 10 else 16
        if 4 + cc_bits + 8 * len(data) <= cap * 8:
            break
    else:
        raise ValueError("too long for a version 1-10 QR code")
    bits: list[int] = []
    put = lambda v, n: bits.extend((v >> i) & 1 for i in reversed(range(n)))  # noqa: E731
    put(0b0100, 4); put(len(data), cc_bits)
    for b in data:
        put(b, 8)
    put(0, min(4, cap * 8 - len(bits)))
    put(0, (-len(bits)) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(words) < cap:
        words.append(pad); pad ^= 0xEC ^ 0x11
    blocks, at, div = [], 0, _rs_divisor(ec)
    for n, k in groups:
        for _ in range(n):
            blk = words[at:at + k]; at += k
            blocks.append((blk, _rs_remainder(blk, div)))
    out = []
    for i in range(max(len(b) for b, _ in blocks)):
        out += [b[i] for b, _ in blocks if i < len(b)]
    for i in range(ec):
        out += [e[i] for _, e in blocks]
    return ver, out


def matrix(text: str) -> list[list[bool]]:
    """The QR code for `text` as rows of booleans (True = dark), without the quiet zone."""
    ver, cw = _codewords(text.encode("utf-8"))
    size = ver * 4 + 17
    mod = [[False] * size for _ in range(size)]
    fn = [[False] * size for _ in range(size)]

    def setf(x, y, dark):
        mod[y][x] = dark; fn[y][x] = True

    for i in range(size):
        setf(6, i, i % 2 == 0); setf(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                if 0 <= cx + dx < size and 0 <= cy + dy < size:
                    setf(cx + dx, cy + dy, max(abs(dx), abs(dy)) not in (2, 4))
    pos = _ALIGN[ver]; last = len(pos) - 1
    for i, ax in enumerate(pos):
        for j, ay in enumerate(pos):
            if (i, j) in ((0, 0), (0, last), (last, 0)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    setf(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)

    def fmt(mask):
        data = (0 << 3) | mask   # level M = 00
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        b = ((data << 10) | rem) ^ 0x5412
        g = lambda i: (b >> i) & 1 == 1  # noqa: E731
        for i in range(6):
            setf(8, i, g(i))
        setf(8, 7, g(6)); setf(8, 8, g(7)); setf(7, 8, g(8))
        for i in range(9, 15):
            setf(14 - i, 8, g(i))
        for i in range(8):
            setf(size - 1 - i, 8, g(i))
        for i in range(8, 15):
            setf(8, size - 15 + i, g(i))
        setf(8, size - 8, True)

    fmt(0)
    if ver >= 7:
        rem = ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        b = (ver << 12) | rem
        for i in range(18):
            bit = (b >> i) & 1 == 1
            a, c = size - 11 + i % 3, i // 3
            setf(a, c, bit); setf(c, a, bit)
    i, nbits, right = 0, len(cw) * 8, size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            for j in range(2):
                x = right - j
                y = size - 1 - vert if ((right + 1) & 2) == 0 else vert
                if not fn[y][x] and i < nbits:
                    mod[y][x] = (cw[i >> 3] >> (7 - (i & 7))) & 1 == 1
                    i += 1
        right -= 2

    def masked(m):
        return [[mod[y][x] ^ (not fn[y][x] and _MASKS[m](x, y)) for x in range(size)] for y in range(size)]

    def penalty(g):
        p = 0
        for lines in (g, [list(c) for c in zip(*g)]):
            for row in lines:
                run, prev = 0, None
                for v in row:
                    if v == prev:
                        run += 1
                    else:
                        if run >= 5:
                            p += run - 2
                        run, prev = 1, v
                if run >= 5:
                    p += run - 2
                s = "".join("1" if v else "0" for v in row)
                p += 40 * (s.count("10111010000") + s.count("00001011101"))
        for y in range(size - 1):
            for x in range(size - 1):
                if g[y][x] == g[y][x + 1] == g[y + 1][x] == g[y + 1][x + 1]:
                    p += 3
        dark = sum(map(sum, g))
        p += abs(dark * 20 - size * size * 10) // (size * size) * 10
        return p

    best = None
    for m in range(8):
        fmt(m)
        g = masked(m)
        sc = penalty(g)
        if best is None or sc < best[0]:
            best = (sc, m, g)
    fmt(best[1])
    return masked(best[1])


def svg(text: str, title: str = "QR code", border: int = 4, dark: str = "#000", light: str = "#fff") -> str:
    """A crisp, scalable SVG (one path) for `text`, with a 4-module quiet zone."""
    g = matrix(text)
    n = len(g) + 2 * border
    runs = []   # one "M x y h n v1 h-n z" per horizontal run of dark modules
    for y, row in enumerate(g):
        x = 0
        while x < len(row):
            if row[x]:
                s = x
                while x < len(row) and row[x]:
                    x += 1
                runs.append(f"M{s + border} {y + border}h{x - s}v1h-{x - s}z")
            else:
                x += 1
    d = "".join(runs)
    t = title.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges" role="img">'
            f'<title>{t}</title><rect width="{n}" height="{n}" fill="{light}"/><path d="{d}" fill="{dark}"/></svg>')
