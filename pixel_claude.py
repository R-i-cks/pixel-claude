#!/usr/bin/env python3
"""Pixel Claude and a friend: two little terminal companions. Run: python3 pixel_claude.py (Ctrl-C quits).

The art and behaviour live here; pixel_claude_gtk.py shows them as a native desktop widget (and adds the toys).
Terminal-only desktop widget through kitty, bottom-right of a 1920x1080 screen; stop with pkill -f pixel_claude:
  kitten panel --edge=none --layer=top --columns=520px --lines=230px --margin-left=1400 --margin-top=790 \
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
       "k": (36, 26, 26), "s": (255, 186, 128), "w": CREAM, "e": SHADE, "a": (170, 236, 255),  # a: power glow
       "p": (255, 128, 170), "y": (255, 214, 90), "g": (96, 176, 96), "h": (240, 80, 100),
       "n": (150, 104, 70), "m": (140, 146, 164), "t": (188, 194, 208),
       "r": (72, 168, 186), "b": (64, 104, 156), "v": (40, 70, 112)}  # r: chair stripes, b/v: book cover, spine
FRIEND = {**PAL, "o": (184, 164, 228), "l": (212, 198, 242), "d": (136, 114, 186), "c": (246, 150, 186),
          "r": (255, 196, 92), "b": (206, 88, 112), "v": (150, 56, 80)}
FUSION = {**PAL, **{k: tuple((x + y) // 2 for x, y in zip(PAL[k], FRIEND[k])) for k in "oldc"}}  # both, blended
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
# deck chair drawn behind the body, starting 2 rows above the head
CHAIR = ["...rwwrrwwrrwwr..."] + ["..rrwwrrwwrrwwrr.."] * 7 + [".nn............nn."] + [".n..............n."] * 3
BOOK = ["ebbbvvbbbe"] * 4  # open book held up, seen from behind: page edges, covers, spine
LAPTOP = [".mmmmmmmmmm.", ".mmmmssmmmm.", ".mmmmssmmmm.", ".mmmmmmmmmm.", "tttttttttttt"]
TAILS = {True: ["..", "ww", "ww", "..", "w."], False: ["www", "ww.", "w.."]}  # thought dots, speech wedge
assert all(len(r) == 18 and set(r) <= {".", *PAL} for r in BODY + CHAIR) and all(len(r) == 7 for r in SPARK)

TOY = 7  # toys are squares this many art pixels wide, drawn at twice the detail: only the native widget can
_M = ["X...X", "XX.XX", "XXXXX", "X.X.X", "X...X"]
TOYS = {  # name -> (14x14 grid, palette): pixel doodles that nod at other logos, no more than that
    "python": ([".....BBBB.....", "....BBBBBB....", "....BBBWKB....", "....BBBBBBRR..", ".....BBBB.....",
                ".....bbbb.....", "...BBBBBBBB...", "...bbbbbbbb...", "..YYYYYYYYYY..", "..yyyyyyyyyy..",
                ".BBBBBBBBBBBB.", ".bbbbbbbbbbbb.", "YYYYYYYYYYYYYY", "yyyyyyyyyyyyyy"],
               {"B": (64, 128, 186), "b": (44, 92, 140), "Y": (255, 212, 59), "y": (214, 170, 30),
                "W": (255, 255, 255), "K": (30, 30, 40), "R": (230, 60, 70)}),
    "hugging face": (["..............", "....YYYYYY....", "..YYYYYYYYYY..", ".YYYYYYYYYYYY.", ".YYYYYYYYYYYY.",
                      "YYYKKYYYYKKYYY", "YYYKKYYYYKKYYY", "YYYYYYYYYYYYYY", "YYYYKYYYYKYYYY", "YYYYYKKKKYYYYY",
                      ".YYYYYRRYYYYY.", "OOOYYYYYYYYOOO", "OOOOYYYYYYOOOO", ".OOO.YYYY.OOO."],
                     {"Y": (255, 210, 30), "O": (255, 157, 0), "K": (58, 59, 69), "R": (230, 80, 80)}),
    "github": (["..............", ".KK........KK.", ".KKK......KKK.", ".KKKKKKKKKKKK.", "KKKKKKKKKKKKKK",
                "KKWWWWWWWWWWKK", "KWWKKWWWWKKWWK", "KWWKKWWWWKKWWK", "KWWWWWKKWWWWWK", "KKWWWWWWWWWWKK",
                ".KKKKKKKKKKKK.", "..KKKKKKKKKK..", "..KK.KK.KK.KK.", "..K..K..K..K.."],
               {"K": (52, 58, 68), "W": (240, 246, 252)}),
    "deepseek": (["..............", "..............", "..............", "....A..A......", ".....AA.......",
                  "......A.......", "...BBBBBBB..BB", "..BBBBBBBBB.BB", ".BBBBBBBBBBBB.", "BBKBBBBBBBBBB.",
                  "BBBBBBBBBBBB..", "BWWWWBBBBBB...", ".WWWWWWBBB....", "..WWWWWW......"],
                 {"B": (77, 107, 254), "A": (160, 204, 255), "W": (228, 236, 255), "K": (20, 24, 60)}),
    "mistral": (["." * 14] * 4 + [".." + "".join(c * 2 if x == "X" else ".." for x in row) + ".."
                                for row, c in zip(_M, "YAORD") for _ in "12"],
                {"Y": (255, 215, 0), "A": (255, 175, 0), "O": (255, 130, 5), "R": (250, 80, 15), "D": (225, 5, 0)}),
    "openai": ([".....GGGG.....", "...GGGGGGGG...", "..GGWWWWGGGG..", ".GGWGGGGWWGGG.", ".GWGGWWGGGWGG.",
                "GGWGWGGWGGWGGG", "GGWGWGGGWGWGGG", "GGGWGWGGGWGWGG", "GGGWGGWGGWGWGG", ".GGWGGGWWGGWG.",
                ".GGGWWGGGGWGG.", "..GGGGWWWWGG..", "...GGGGGGGG...", ".....GGGG....."],
               {"G": (16, 163, 127), "W": (255, 255, 255)}),
}
assert all(len(g) == 14 and all(len(r) == 14 and set(r) <= {".", *pal} for r in g) for g, pal in TOYS.values())
GLYPHS = "01<>/=+*#$"  # the falling code while they are fused
FIRE = (255, 236, 120), (255, 160, 40), (236, 78, 24)
BURN = 1.8  # seconds from the first flame to a toy being gone
HEAR, DRACARYS = 1.6, 4.6  # the finale: seconds until they open fire, and until nothing is left
SLOTS = (0.0, 0.1, 0.2, 0.8, 0.9, 1.0)  # where a toy can sit, as a fraction of the floor: off to the sides
AWAY, FUSED = 12, 7  # seconds one stays off the screen, seconds the two stay fused
STILL = ("watch", "read", "study", "sun", "sleep")  # calm moods: no bobbing, and they last much longer
MOODS = {"watch": 6, "read": 6, "study": 5, "sun": 4, "sleep": 3, "idle": 3,
         "walk": 1, "wave": 1, "think": 1, "idea": 1, "flowers": 2, "leave": 2, "play": 2, "fuse": 2}
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


def sprite(look=0, blink=False, step=0, wave=0, shades=False, down=0, glint=False, glow=False):
    g = [list(r) for r in BODY]
    for x in (5, 11):
        for y in (3 + down,) if blink else (2 + down, 3 + down):
            g[y][x + look] = g[y][x + look + 1] = "a" if glow else "k"
        if glint and not blink:
            g[2][x] = "w"
    if glow:  # glowing eyes and a mark on the forehead
        g[0][8] = g[0][9] = g[1][8] = g[1][9] = "a"
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


def scatter(names):
    """Up to three random toys on random floor slots, as (name, slot) pairs."""
    n = min(3, len(names))
    return list(zip(random.sample(list(names), n), random.sample(SLOTS, n)))


def new_state(names=()):
    """names: the toys that exist (none in a terminal)."""
    return SimpleNamespace(cs=[SimpleNamespace(x=None, d=1, run=False), SimpleNamespace(x=None, d=-1, run=False)],
                           names=list(names), toys=scatter(names), homes=[0.0, 0.0], burn=None, done=False,
                           mood="watch", who=0, phase=0, mark=0.0, start=0.0, until=6.0, line="")


def greet(st, who, t):
    """Someone poked creature `who`: it waves and says hi. Ignored mid-trip and mid-fusion."""
    if st.mood not in ("leave", "fuse"):
        st.mood, st.who, st.phase, st.start, st.until = "wave", who, 0, t, t + 3.5
        st.line = random.choice(HELLOS)


def ignite(st, name, t):
    """The mouse is on that toy: one of them firebends it away. One fire at a time, and not while fused."""
    if st.burn is None and st.mood != "fuse" and name in dict(st.toys):
        st.burn = (name, t)


def farewell(st, t):
    """Sent away: they hear "dracarys" from outside and burn each other to nothing; update() then sets st.done."""
    if st.mood != "dracarys":
        if st.mood in ("leave", "fuse"):  # mid-trip or fused: put both back on their spots first
            st.cs[0].x, st.cs[1].x = st.homes
        st.mood, st.phase, st.start, st.until, st.burn = "dracarys", 0, t, t + 999, None


def ashes(st, t):
    """1 while they are whole; in the finale it falls to 0 as they burn away."""
    if st.mood != "dracarys":
        return 1
    return 1 - max(0, min(1, (t - st.start - HEAR - 0.8) / (DRACARYS - HEAR - 0.8)))


def toss(st, t):
    """Play: where the tossed toy is between them, 0 = at the left one, 1 = at the right one."""
    return abs((t - st.start) * 0.7 % 2 - 1)


def power(st, t):
    """0..1: how deep in meditation the one left behind is while the other is off the screen."""
    if st.mood != "leave" or st.phase != 1:
        return 0
    return max(0, min(1, (t - st.mark) / 1.5, (AWAY - (t - st.mark)) / 1.5))


def toy_spots(t, st, w, h, s=1):
    """Where the native widget draws each toy: (name, x, y, in_front, opacity); x, y its top-left in art pixels."""
    gy, out, force = h - 1, [], power(st, t)
    for k, (name, slot) in enumerate(st.toys):
        x, y, front = slot * (w - TOY * s), gy - TOY * s, False
        if st.mood == "play" and k == 0:  # tossed in an arc from head to head
            ax, bx = (c.x + (9 - TOY / 2) * s for c in st.cs)
            x, y = ax + (bx - ax) * toss(st, t), gy - (10 + TOY) * s - math.sin(math.pi * toss(st, t)) * 6 * s
        elif force:  # lifted off the floor into an orbit around the one meditating
            c, turn = st.cs[1 - st.who], t * 1.6 + k * 2 * math.pi / len(st.toys)
            ox = c.x + (9 - TOY / 2) * s + math.cos(turn) * 16 * s
            oy = gy - (9 + TOY / 2) * s + math.sin(turn) * 3 * s
            x, y, front = x + (ox - x) * force, y + (oy - y) * force, math.sin(turn) > 0
        age = t - st.burn[1] if st.burn and st.burn[0] == name else 0  # a burning toy fades once the fire is on it
        out.append((name, x, y, front, (1 - max(0, min(1, (age - 0.5) / (BURN - 0.5)))) * ashes(st, t)))
    return out


def rain(texts, t, x0, x1, rows, hole):
    """Falling code over text columns x0..x1; `hole` = (x0, x1, top row) is a box it leaves clear."""
    for col in range(x0, x1, 2):
        head = int(t * (6 + col * 7 % 5) + col * 13 % 17) % (rows + 8)
        for k in range(6):  # a bright head and a fading tail
            row = head - k
            if 0 <= row < rows and not (hole[0] <= col < hole[1] and row >= hole[2]):
                glyph = GLYPHS[(col * 31 + row * 17 + int(t * 6)) % len(GLYPHS)]
                texts.append((col, row, glyph, mix((0, 230, 80), (0, 60, 30), k / 6) if k else (200, 255, 210), None))


def flames(px, t, sx, sy, tx, ty, s, reach):
    """A jet of fire from (sx, sy) toward (tx, ty), `reach` 0..1 of the way there, with a blaze once it lands."""
    n = max(1, int(math.hypot(tx - sx, ty - sy) / s))
    for j in range(int(n * reach) + 1):
        y = sy + (ty - sy) * j / n + math.sin(j * 1.3 + t * 20) * s
        blit(px, ["f"], int(sx + (tx - sx) * j / n), int(y), s, {"f": FIRE[(j + int(t * 15)) % 3]})
    for q in range(14 if reach == 1 else 0):
        cell = (q * 37 + int(t * 12) * 17) % 49  # a different handful of the toy's 7x7 cells every frame
        blit(px, ["f"], int(tx - 3.5 * s) + cell % 7 * s, int(ty - 4.5 * s) + cell // 7 * s, s,
             {"f": FIRE[(q + int(t * 12)) % 3]})


def update(st, t, dt, w, s, cursor=None):
    """cursor: x of the mouse pointer in art pixels while it is over one of them, else None."""
    span, gap = max(0, w - 18 * s), 19 * s
    a, b = st.cs  # a stays left of b, except during a trip off the screen or a fusion
    if a.x is None:
        a.x, b.x = span / 2 - 12 * s, span / 2 + 12 * s
    if st.mood == "dracarys":  # the finale runs on its own clock; nothing else moves
        a.run = b.run = False
        st.done = t - st.start > DRACARYS
        return
    if t >= st.until:
        moods = {k: v for k, v in MOODS.items() if st.toys or k != "play"}
        st.mood = random.choices(list(moods), list(moods.values()))[0]
        st.who, st.phase, st.mark, st.start, st.homes = random.randrange(2), 0, t, t, [a.x, b.x]
        a.d, b.d = random.choice((-1, 1)), random.choice((-1, 1))
        st.line = random.choice(HELLOS if st.mood == "wave" else THOUGHTS)
        st.until = t + (random.uniform(20, 45) if st.mood in STILL else
                        {"flowers": 60, "leave": 120, "fuse": 120, "play": 8}.get(
                            st.mood, random.uniform(3, 6) + (st.mood == "think") * len(st.line) / 14))
    if st.burn and t - st.burn[1] > BURN:  # burnt away; whoever next comes back from a trip brings new ones
        st.toys, st.burn = [toy for toy in st.toys if toy[0] != st.burn[0]], None
    if st.mood == "play" and not st.toys:
        st.until = t  # nothing left to toss
    me, you = st.cs[st.who], st.cs[1 - st.who]
    room = lambda c: (0, b.x - gap) if c is a else (a.x + gap, span)
    if st.mood == "flowers" and not st.phase:
        me.d = 1 if you.x > me.x else -1
        if abs(you.x - me.x) > 21 * s:
            me.x += me.d * 9 * s * dt
        elif t - st.start > 1.5:  # already close: holds it out for a moment, then hands it over
            st.phase, st.mark, st.until = 1, t, t + 3.5
    elif st.mood == "leave":  # phases: 0 walk off the right edge, 1 away, 2 walk back, 3 home
        if st.phase in (0, 2):
            me.d = 1 - st.phase
            me.x += me.d * 9 * s * dt
            if st.phase == 0 and me.x > w + s:
                st.phase, st.mark = 1, t
            elif st.phase == 2 and me.x <= st.homes[st.who]:  # back, and it brought new toys
                me.x, st.phase, st.until, st.toys = st.homes[st.who], 3, t + 1.5, scatter(st.names)
        elif st.phase == 1 and t - st.mark > AWAY:
            st.phase = 2
    elif st.mood == "fuse":  # phases: 0 walk into each other, 1 fused, 2 walk apart, 3 home
        if st.phase in (0, 2):
            goals = st.homes if st.phase else [sum(st.homes) / 2] * 2
            for c, goal in zip(st.cs, goals):
                c.d = 1 if goal > c.x else -1
                c.x = goal if abs(goal - c.x) <= 9 * s * dt else c.x + c.d * 9 * s * dt
            if [a.x, b.x] == goals:
                st.phase, st.mark = st.phase + 1, t
                if st.phase == 3:
                    st.until = t + 1
        elif st.phase == 1 and t - st.mark > FUSED:
            st.phase, st.mark = 2, t
    elif st.mood == "walk":
        for c in st.cs:
            lo, hi = room(c)
            c.x += c.d * 7 * s * dt
            if not lo <= c.x <= hi:
                c.d, c.x = -c.d, min(max(c.x, lo), hi)
    for c in st.cs:
        # scurries out from under the mouse pointer (not mid-trip or mid-fusion: those are choreographed)
        c.run = cursor is not None and st.mood not in ("leave", "fuse") and c.x - 2 * s <= cursor <= c.x + 20 * s
        if c.run:
            lo, hi = room(c)
            c.d = 1 if cursor < c.x + 9 * s else -1
            c.x = min(max(c.x + c.d * 24 * s * dt, lo), hi)
        if not (st.mood == "leave" and c is me):
            c.x = min(max(c.x, 0), span)


def scene(t, st, w, h, s, sky=True):
    """Returns (pixels, texts): h pixel rows of RGB (None = transparent), and (col, row, text, fg, bg) overlays."""
    m, e = st.mood, t - st.start
    me = st.cs[st.who]
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

    texts, base, force = [], (gy - 10 * s) // 2, power(st, t)
    fused = m == "fuse" and st.phase == 1
    fire = None  # (who bends, target x, target y): the on-screen one nearest the burning toy
    if st.burn and not fused:
        tx, ty = next((x + TOY * s / 2, y + TOY * s / 2)
                      for name, x, y, *_ in toy_spots(t, st, w, h, s) if name == st.burn[0])
        fire = min((i for i, c in enumerate(st.cs) if c.x <= w), key=lambda i: abs(st.cs[i].x + 9 * s - tx)), tx, ty
    drac, ash = m == "dracarys", ashes(st, t)
    lit = drac and e >= HEAR
    for i, c in enumerate(() if fused else st.cs):
        mine, toward, pal = c is me, 1 if st.cs[1 - i].x > c.x else -1, (PAL, FRIEND)[i]
        given = m == "flowers" and st.phase
        hop = m == "idea" and mine or given and not mine
        far = abs(st.cs[0].x - st.cs[1].x) > 21 * s
        walking = c.run or m == "walk" or m == "fuse" and st.phase in (0, 2) or mine and (
            m == "flowers" and not given and far or m == "leave" and st.phase in (0, 2))
        zen = m == "leave" and st.phase == 1 and not mine  # left alone: meditates, levitating
        prop = (LAPTOP if mine else BOOK) if m == "study" else BOOK if m == "read" else None
        if hop:
            lift = int(abs(math.sin(t * 7)) * 2 * s)
        elif zen:
            lift = int(force * (4 + math.sin(t * 1.5)) * s)
        else:
            lift = int(m not in STILL and math.sin(t * 1.2 + i) > 0)
        x0, top = int(c.x), gy - 10 * s - lift
        for x in range(max(0, x0 + 2 * s + lift), min(w, x0 + 16 * s - lift)) if ash > 0.3 else ():
            px[gy][x] = GND1  # shadow, shrinks as it rises
        if m == "sun":
            blit(px, CHAIR, x0, top - 2 * s, s, pal, fade)

        bending = bool(fire) and fire[0] == i
        if bending:
            look = 1 if fire[1] > c.x + 9 * s else -1
        elif drac:
            look = toward if lit else 1  # first toward the voice from past the right edge, then at each other
        elif walking:
            look = c.d
        elif prop:
            look = (-1, 0, 1, 0)[int(t / 1.5 + i) % 4]  # eyes scan the page
        elif m in STILL or zen:
            look = 0
        elif m == "idle":
            look = (0, 0, -1, 0, 0, 1)[int(t / 1.2 + i * 2) % 6]
        else:
            look = toward
        waving = m == "wave" and (mine or e > 1) or m == "leave" and not mine and st.phase in (0, 2)  # bye / welcome back
        catching = m == "play" and (toss(st, t) < 0.2 if i == 0 else toss(st, t) > 0.8)  # arm up as the toy arrives
        blit(px, sprite(look, not bending and (m == "sleep" or zen and force < 0.5 or (t + i * 1.3) % 3.7 < 0.15),
                        1 + int(t * 6 + i) % 2 if walking else 0,
                        3 if catching else 1 + 2 * (int(t * 5) % 2) if waving else 0,
                        m == "sun" and fade > 0.5, bool(prop), m == "watch" or drac and not lit,
                        bending or lit or zen and force >= 0.5), x0, top, s, pal, ash)
        if bending:  # the jet leaves from the arm on the toy's side
            flames(px, t, x0 + (17 if look > 0 else 0) * s, top + 4 * s, fire[1], fire[2], s,
                   min(1, (t - st.burn[1]) / 0.4))

        if prop:
            blit(px, prop, x0 + (18 - len(prop[0])) // 2 * s, top + 5 * s, s, pal, fade)
        elif m == "idea" and mine:
            spark(px, x0 + 11 * s // 2, top - 9 * s, s, int(t * 6) % 2)
        elif m == "flowers" and mine != bool(given):  # giver carries it, then the other one holds it
            blit(px, FLOWER, x0 + (17 * s if toward > 0 else -2 * s), top + s, s)
        elif m == "sleep":
            for j in range(3):
                p = (t * 0.4 + j / 3 + i / 2) % 1
                texts.append((x0 + 15 * s + int(p * 8), base - int(p * 5), "zZ"[p > 0.5], mix(CREAM, SKY0, p), None))

    if drac and not lit:
        bubble(px, texts, w - 3, base - 4, "DRACARYS!", False)  # shouted from off the screen
    for c, other in (st.cs, st.cs[::-1]) if lit else ():  # both open fire on each other
        arm = int(c.x) + (17 if other.x > c.x else 0) * s
        flames(px, t, arm, gy - 6 * s, other.x + 9 * s, gy - 5 * s, s, min(1, (e - HEAR) / 0.4))
    if m == "fuse" and st.phase in (1, 2):
        x0 = int(sum(st.homes) / 2) - 9 * s  # the fused one is twice the size, centred where they met
        if fused:
            top = gy - 20 * s - int(math.sin(t * 1.2) > 0) * s
            for x in range(max(0, x0 + 4 * s), min(w, x0 + 32 * s)):
                px[gy][x] = GND1
            big, tear = sprite(shades=True), s * (int(t * 10) % 9 == 0)  # now and then the picture tears
            blit(px, big[:5], x0 + tear, top, 2 * s, FUSION)
            blit(px, big[5:], x0 - tear, top + 10 * s, 2 * s, FUSION)
            rain(texts, t, max(0, x0 - 6 * s), min(w, x0 + 42 * s), h // 2, (x0 + 6 * s, x0 + 30 * s, top // 2))
        if t - st.mark < 0.5:  # flash as they merge and as they split
            spark(px, x0 + 11 * s, gy - 17 * s, 2 * s, int(t * 12) % 2)
    if m == "flowers" and st.phase:
        age = t - st.mark
        blit(px, HEART, int(st.cs[0].x + st.cs[1].x) // 2 + 13 * s // 2, gy - 16 * s - int(age * 3 * s), s, v=1 - age / 3.5)
    if m in ("think", "wave"):  # typed out letter by letter inside a full-width balloon
        bubble(px, texts, int(me.x) + 9 * s, base - 4, st.line[:int(e * 14)].ljust(len(st.line)), m == "think")
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
    st, sky = new_state(), "--widget" not in sys.argv
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
