#!/usr/bin/env python3
"""Pixel Claude and a friend: two little terminal companions. Run: python3 pixel_claude.py (Ctrl-C quits).

Desktop widget (transparent, no sky), bottom-right of a 1920x1080 screen; stop with pkill -f pixel_claude:
  kitten panel --edge=none --layer=top --columns=520px --lines=230px --margin-left=1376 --margin-top=790 \
    -o background_opacity=0 -o window_padding_width=0 -o font_size=10 --detach \
    python3 ~/Projects/pixel-claude/pixel_claude.py --widget
"""
import math
import random
import shutil
import sys
import time
from types import SimpleNamespace

CREAM, SHADE = (250, 240, 225), (216, 200, 182)
PAL = {"o": (217, 119, 87), "l": (240, 158, 124), "d": (166, 82, 58), "c": (238, 132, 118),
       "k": (36, 26, 26), "s": (255, 186, 128), "w": CREAM,
       "p": (255, 128, 170), "y": (255, 214, 90), "g": (96, 176, 96), "h": (240, 80, 100)}
FRIEND = {**PAL, "o": (106, 155, 204), "l": (156, 194, 230), "d": (70, 110, 160), "c": (240, 150, 175)}
SUN = {**PAL, "s": PAL["y"]}
NIGHT = SKY0, SKY1, GND0, GND1 = (10, 12, 36), (96, 56, 110), (40, 30, 58), (16, 12, 28)
DAY = (86, 160, 226), (252, 206, 160), (226, 196, 140), (186, 154, 104)  # sky top, horizon, sand, sand edge
BODY = [  # eyes and arms are added per frame in sprite()
    "....llllllllll....",
    "...oooooooooooo...",
    "...oooooooooooo...",
    "...oooooooooooo...",
    "...ocooooooooco...",
    "...oooooooooooo...",
    "...oooooooooooo...",
    "...dddddddddddd...",
    "...d.d......d.d...",
    "...d.d......d.d...",
]
SPARK = [
    "...s...",
    ".s.s.s.",
    "..sss..",
    "sssssss",
    "..sss..",
    ".s.s.s.",
    "...s...",
]
FLOWER = [".p.", "pyp", ".p.", ".g.", ".g."]
HEART = [".h.h.", "hhhhh", ".hhh.", "..h.."]
TAILS = {True: ["..", "ww", "ww", "..", "w."], False: ["www", "ww.", "w.."]}  # thought dots, speech wedge
assert all(len(r) == 18 and set(r) <= {".", *PAL} for r in BODY) and all(len(r) == 7 for r in SPARK)

MOODS = {"idle": 2, "walk": 4, "wave": 2, "think": 2, "idea": 1, "sleep": 1, "flowers": 3, "sun": 2, "vanish": 2}
HELLOS = ["hi!", "hello!", "olá!", "oh, it's you :)"]
THOUGHTS = [
    "the best code is no code",
    "hmm, what if we just deleted it",
    "you're absolutely right!",
    "tabs or spaces today?",
    "it works on my terminal",
    "one more test, then tea",
    "naming things is hard",
    "I wonder what stars compile to",
]
STARS = [(random.random(), random.random(), random.random() * 6.28) for _ in range(400)]


def mix(a, b, f):
    return tuple(int(x + (y - x) * f) for x, y in zip(a, b))


def sprite(look, blink, step, wave, shades):
    g = [list(r) for r in BODY]
    for x in (5, 11):
        for y in (3,) if blink else (2, 3):
            g[y][x + look] = g[y][x + look + 1] = "k"
    if shades:
        g[2][4:14] = "k" * 10
    for y in (4, 5):
        g[y][1] = g[y][2] = g[y - wave][15] = g[y - wave][16] = "o"
    if step:
        for x in ((3, 12), (5, 14))[step - 1]:
            g[9][x] = "."
    return g


def blit(px, grid, x0, y0, s, pal=PAL, v=1):
    """v < 1 dissolves the grid: only a fixed pseudo-random fraction of its pixels is drawn."""
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch != "." and (gx * 7 + gy * 13) % 10 < v * 10:
                for y in range(y0 + gy * s, y0 + gy * s + s):
                    for x in range(x0 + gx * s, x0 + gx * s + s):
                        if 0 <= y < len(px) and 0 <= x < len(px[0]):
                            px[y][x] = pal[ch]


def spark(px, x0, y0, s, k, pal=PAL, v=1):
    # k=1 draws the 5px core, so alternating k pulses it
    blit(px, [r[k:7 - k] for r in SPARK[k:7 - k]], x0 + k * s, y0 + k * s, s, pal, v)


def bubble(px, texts, mid, row, txt, thought):
    """Rounded pixel balloon holding txt on text row `row`; its tail drops toward pixel column `mid`."""
    w, n, y0 = len(px[0]), len(txt) + 2, row * 2 - 1
    x0 = max(0, min(mid - n // 2, w - n))  # stays on screen; the tail still follows the speaker
    for y in range(max(0, y0), min(len(px), y0 + 4)):
        for x in range(x0, min(w, x0 + n)):
            if not (y in (y0, y0 + 3) and x in (x0, x0 + n - 1)):  # clipped corners
                px[y][x] = SHADE if y == y0 + 3 else CREAM
    blit(px, TAILS[thought], max(x0 + 1, min(mid, x0 + n - 4)), y0 + 4, 1)
    texts.append((x0 + 1, row, txt, PAL["k"], None))


def update(st, t, dt, w, s):
    span, gap = max(0, w - 18 * s), 19 * s
    a, b = st.cs  # a always stays left of b
    if a.x is None:
        a.x, b.x = span / 2 - 12 * s, span / 2 + 12 * s
    if t >= st.until:
        st.mood = random.choices(list(MOODS), list(MOODS.values()))[0]
        st.who, st.given, st.moved, st.start = random.randrange(2), None, False, t
        a.d, b.d = random.choice((-1, 1)), random.choice((-1, 1))
        st.line = random.choice(HELLOS if st.mood == "wave" else THOUGHTS)
        st.until = t + {"flowers": 60, "vanish": 5, "sun": 8}.get(
            st.mood, random.uniform(3, 6) + (st.mood == "think") * len(st.line) / 14)
    me, you = st.cs[st.who], st.cs[1 - st.who]
    room = lambda c: (0, b.x - gap) if c is a else (a.x + gap, span)
    if st.mood == "flowers" and not st.given:
        me.d = 1 if you.x > me.x else -1
        if abs(you.x - me.x) > 21 * s:
            me.x += me.d * 9 * s * dt
        else:
            st.given, st.until = t, t + 3.5
    elif st.mood == "walk":
        for c in st.cs:
            lo, hi = room(c)
            c.x += c.d * 7 * s * dt
            if not lo <= c.x <= hi:
                c.d, c.x = -c.d, min(max(c.x, lo), hi)
    elif st.mood == "vanish" and not st.moved and t - st.start > 1.5:
        lo, hi = room(me)  # comes back somewhere else
        me.x, st.moved = random.uniform(lo, max(lo, hi)), True
    for c in st.cs:
        c.x = min(max(c.x, 0), span)


def scene(t, st, w, h, s, sky=True):
    """Returns (pixels, texts): h pixel rows of RGB (None = transparent), and (col, row, text, fg, bg) overlays."""
    m, e = st.mood, t - st.start
    me, you = st.cs[st.who], st.cs[1 - st.who]
    fade = max(0, min(1, e, st.until - t))  # 0 at both ends of a mood, 1 in between
    day = fade * (m == "sun")
    gy = h - max(4, h // 7) if sky else h - 1
    c0, c1, g0, g1 = (mix(n, d, day) for n, d in zip(NIGHT, DAY))
    px = [[(mix(c0, c1, y / gy) if y < gy else mix(g0, g1, (y - gy) / (h - gy))) if sky else None] * w
          for y in range(h)]
    for sx, sy, ph in STARS[: w * gy // 60] if sky else ():
        x, y = int(sx * w), int(sy * gy)
        px[y][x] = mix(px[y][x], CREAM, (0.5 + 0.5 * math.sin(t * 1.5 + ph)) * (1 - day))
    if m == "sun":
        spark(px, w - 10 * s, s, s, int(t * 2) % 2, SUN, fade)

    texts, base = [], (gy - 10 * s) // 2
    for i, c in enumerate(st.cs):
        mine, toward = c is me, 1 if st.cs[1 - i].x > c.x else -1
        hop = m == "idea" and mine or m == "flowers" and st.given and not mine
        lift = int(abs(math.sin(t * 7)) * 2 * s) if hop else int(m not in ("sleep", "sun") and math.sin(t * 2.5 + i) > 0)
        vis = 1 - fade if m == "vanish" and mine else 1
        x0, top = int(c.x), gy - 10 * s - lift
        if vis > 0.5:
            for x in range(max(0, x0 + 2 * s + lift), min(w, x0 + 16 * s - lift)):
                px[gy][x] = GND1  # shadow, shrinks as it hops

        walking = m == "walk" or m == "flowers" and mine and not st.given
        if m in ("sleep", "sun"):
            look = 0
        elif walking:
            look = c.d
        elif m == "idle":
            look = (0, 0, -1, 0, 0, 1)[int(t / 1.2 + i * 2) % 6]
        elif m == "vanish" and not mine and fade == 1:
            look = (-1, 1)[int(t * 2) % 2]  # where did they go?
        else:
            look = toward
        blit(px, sprite(look, m == "sleep" or (t + i * 1.3) % 3.7 < 0.15,
                        1 + int(t * 6 + i) % 2 if walking else 0,
                        1 + 2 * (int(t * 5) % 2) if m == "wave" and (mine or e > 1) else 0,
                        m == "sun" and fade > 0.5), x0, top, s, (PAL, FRIEND)[i], vis)

        if m == "idea" and mine:
            spark(px, x0 + 11 * s // 2, top - 9 * s, s, int(t * 6) % 2)
        elif m == "flowers" and c is (you if st.given else me):
            blit(px, FLOWER, x0 + (17 * s if toward > 0 else -2 * s), top + s, s)
        elif m == "sleep":
            for j in range(3):
                p = (t * 0.4 + j / 3 + i / 2) % 1
                texts.append((x0 + 15 * s + int(p * 8), base - int(p * 5), "zZ"[p > 0.5], mix(CREAM, SKY0, p), None))

    if m == "flowers" and st.given:
        age = t - st.given
        blit(px, HEART, int(me.x + you.x) // 2 + 13 * s // 2, gy - 16 * s - int(age * 3 * s), s, v=1 - age / 3.5)
    if m in ("think", "wave"):  # typed out letter by letter inside a full-width balloon
        bubble(px, texts, int(me.x) + 9 * s, base - 4, st.line[:int(e * 14)].ljust(len(st.line)), m == "think")
    elif m == "vanish" and e > 1:
        bubble(px, texts, int(you.x) + 9 * s, base - 4, "?" if fade == 1 else "!", fade == 1)
    return px, texts


def draw(px, texts):
    # two pixel rows per terminal line: fg paints the top half of "▀", bg the bottom
    w, out = len(px[0]), ["\033[H"]
    for y in range(0, len(px), 2):
        last = None
        for pair in zip(px[y], px[y + 1]):
            if pair != last:
                top, bot = last = pair
                if top and bot:
                    sgr, ch = "\033[38;2;%d;%d;%d;48;2;%d;%d;%dm" % (top + bot), "▀"
                elif top or bot:  # other half transparent: paint only this half, default bg
                    sgr, ch = "\033[0;38;2;%d;%d;%dm" % (top or bot), "▀" if top else "▄"
                else:
                    sgr, ch = "\033[0m", " "
                out.append(sgr)
            out.append(ch)
        out.append("\033[0m\n" if y + 2 < len(px) else "\033[0m")
    for col, row, txt, fg, bg in texts:
        col = max(0, min(col, w - len(txt)))
        if 0 <= row < len(px) // 2:
            bg = bg or px[row * 2][col]
            out.append("\033[%d;%dH\033[0;1;38;2;%d;%d;%dm" % (row + 1, col + 1, *fg)
                       + ("\033[48;2;%d;%d;%dm" % bg if bg else "") + txt + "\033[0m")
    return "".join(out)


def main():
    st = SimpleNamespace(cs=[SimpleNamespace(x=None, d=1), SimpleNamespace(x=None, d=-1)],
                         mood="idle", who=0, given=None, moved=False, start=0.0, until=3.0, line="")
    sky = "--widget" not in sys.argv
    t0 = last = time.monotonic()
    sys.stdout.write("\033[?1049h\033[?25l\033[?7l")  # alt screen, hide cursor, no autowrap
    try:
        while True:
            now = time.monotonic()
            t, dt, last = now - t0, now - last, now
            w, rows = shutil.get_terminal_size()
            rows = max(rows, 3)
            s = max(1, min(4, w // 48, rows // 11))
            update(st, t, dt, w, s)
            sys.stdout.write(draw(*scene(t, st, w, rows * 2, s, sky)))
            sys.stdout.flush()
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?7h\033[?25h\033[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
