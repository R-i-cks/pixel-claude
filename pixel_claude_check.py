"""Self-check for pixel_claude.py and pixel_claude_gtk.py: python3 pixel_claude_check.py"""
import math

import pixel_claude as p

NAMES = ["one", "two", "three", "four"]  # stand-in toys


def state(mood, w, s, who=0, phase=0, until=8.0, xa=None, xb=None, line=p.THOUGHTS[1], names=NAMES):
    span = max(0, w - 18 * s)
    st = p.new_state(names)
    st.cs[0].x = max(0, span / 2 - 12 * s) if xa is None else xa
    st.cs[1].x = max(0, span / 2 + 12 * s) if xb is None else xb
    st.homes = [st.cs[0].x, st.cs[1].x]
    st.mood, st.who, st.phase, st.mark, st.until, st.line = mood, who, phase, 1.0, until, line
    return st


if __name__ == "__main__":
    # 1. every mood x size x mode x actor x phase x time renders with the right shape
    for sky in (True, False):
        for w, rows in [(100, 30), (200, 60), (96, 12), (64, 12), (42, 12), (10, 3), (1, 3)]:
            s = max(1, min(4, w // 48, rows // 11))
            for mood in p.MOODS:
                for who in (0, 1):
                    for phase in (0, 1, 2, 3):
                        for t in [0, 0.1, 0.5, 1.3, 2.9, 4.2, 5.5, 7.6, 7.99]:
                            for off in (0, w + 5):  # also with the actor walked off the right edge
                                st = state(mood, w, s, who, phase)
                                st.cs[who].x += off
                                px, texts = p.scene(t, st, w, rows * 2, s, sky)
                                assert len(px) == rows * 2 and all(len(r) == w for r in px)
                                assert p.draw(px, texts).count('\n') == rows - 1
                                spots = p.toy_spots(t, st, w, rows * 2, s)
                                assert len(spots) == 3 and all(math.isfinite(x + y) for _, x, y, *_ in spots)
                                for col, row, txt, fg, bg in texts:  # balloon text sits on balloon pixels
                                    if mood in ("think", "wave") and w >= 42:
                                        assert 0 <= col and col + len(txt) <= w and px[row * 2][col] == p.CREAM, (mood, w, col)

    # 2. long simulated runs, with and without toys: every mood reached, bounds and left/right order hold,
    #    flowers get handed over, trips and fusions always finish back home, calm moods dominate
    for w, s, names in [(96, 1, NAMES), (64, 1, ()), (100, 2, NAMES), (200, 4, ())]:
        st = p.new_state(names)
        st.mood, st.until = "idle", 0.0
        t, seen, count, calm, span, n = 0, set(), dict(flowers=0, leave=0, fuse=0), 0, w - 18 * s, 120000
        for step in range(n):
            t += 1 / 15
            was, began, homes, stood = (st.mood, st.phase), st.start, list(st.homes), [c.x for c in st.cs]
            if step % 900 == 0 and st.toys:  # now and then the mouse burns a toy
                p.ignite(st, st.toys[0][0], t)
            p.update(st, t, 1 / 15, w, s)
            seen.add(st.mood)
            calm += st.mood in p.STILL or st.mood == "idle"
            if st.mood in count and st.phase == 1 and was == (st.mood, 0):
                count[st.mood] += 1
            a, b = st.cs
            if st.start != began and was[0] in ("leave", "fuse"):  # these two always run to the end, back home
                assert was[1] == 3 and stood == homes, (was, stood, homes)
            away = st.mood == "leave" and st.phase < 3
            for c in st.cs:
                assert away and c is st.cs[st.who] or 0 <= c.x <= span, (st.mood, st.phase, c.x)
            assert away or a.x < b.x or st.mood == "fuse" and a.x <= b.x, (st.mood, a.x, b.x)
            assert st.until - st.start < 121
            assert len(st.toys) <= min(3, len(names)) and len(st.toys) == len({name for name, _ in st.toys})
            assert 0 <= p.power(st, t) <= 1 and 0 <= p.toss(st, t) <= 1
            p.scene(t, st, w, 24 * s, s, False)
            p.toy_spots(t, st, w, 24 * s, s)
        assert seen == set(p.MOODS) - ({"play"} if not names else set()), seen
        assert all(count.values()) and calm / n > 0.8, (count, calm / n)
        print(f"{w} cols, scale {s}, {len(names)} toys: {count['flowers']} flowers, {count['leave']} trips, "
              f"{count['fuse']} fusions, {calm / n:.0%} of the time calm")

    # 3. a poke makes that one wave, except mid-trip and mid-fusion
    st = state("read", 65, 1)
    p.greet(st, 1, 5.0)
    assert (st.mood, st.who, st.start) == ("wave", 1, 5.0) and st.line in p.HELLOS
    for busy in ("leave", "fuse"):
        st = state(busy, 65, 1, phase=1)
        p.greet(st, 0, 5.0)
        assert st.mood == busy

    # 4. meditation: full power mid-absence, none at its edges; toys leave the floor and come back
    st = state("leave", 96, 1, who=1, phase=1)
    assert p.power(st, 1.0) == 0 and p.power(st, 1.0 + p.AWAY / 2) == 1 and p.power(st, 1.0 + p.AWAY) == 0
    floor = [y for _, _, y, *_ in p.toy_spots(1.0, st, 96, 24)]
    assert all(y < f for (_, _, y, *_), f in zip(p.toy_spots(1.0 + p.AWAY / 2, st, 96, 24), floor))
    assert [y for _, _, y, *_ in p.toy_spots(1.0 + p.AWAY, st, 96, 24)] == floor

    # 5. the mouse pointer shoos them: they move away from it, keep their order and stay on screen,
    #    but hold still mid-trip and mid-fusion
    st = state("read", 96, 1)
    (a, b), x = st.cs, st.cs[0].x
    p.update(st, 2.0, 1 / 15, 96, 1, cursor=x + 12)  # pointer on the right half of the left one
    assert a.run and not b.run and a.d == -1 and a.x < x
    for _ in range(40):
        p.update(st, 2.0, 1 / 15, 96, 1, cursor=x + 12)
        assert 0 <= a.x < b.x <= 96 - 18
    assert a.x + 20 < x + 12 and not a.run  # it got clear of the pointer and stopped
    for busy in ("leave", "fuse"):
        st = state(busy, 96, 1, phase=1, until=99)
        x = st.cs[1].x
        p.update(st, 2.0, 1 / 15, 96, 1, cursor=x + 9)
        assert st.cs[1].x == x and not st.cs[1].run

    # 6. the fused one brings falling code, and none of it lands on its body
    st = state("fuse", 96, 1, phase=1, until=99)
    px, texts = p.scene(3.0, st, 96, 24, 1, False)
    assert len(texts) > 20 and all(ch in p.GLYPHS and 0 <= col < 96 and 0 <= row < 12 for col, row, ch, _, _ in texts)
    assert all(px[row * 2][col] is None or row * 2 < 2 for col, row, *_ in texts if 43 <= col < 53)

    # 7. firebending: the mouse on a toy sets it alight (one fire at a time, none while fused);
    #    flames show, the toy fades and is gone, and the rest stay
    st = state("read", 96, 1, until=99)
    name, other = st.toys[0][0], st.toys[1][0]
    p.ignite(st, name, 2.0)
    p.ignite(st, other, 2.1)
    assert st.burn == (name, 2.0)
    px, _ = p.scene(3.0, st, 96, 24, 1, False)
    assert sum(c in p.FIRE for row in px for c in row) > 10
    fading = [dict((n, a) for n, _, _, _, a in p.toy_spots(2.0 + k, st, 96, 24))[name] for k in (0.2, 1.0, 1.7)]
    assert fading[0] == 1 > fading[1] > fading[2] > 0
    p.update(st, 2.0 + p.BURN + 0.1, 1 / 15, 96, 1)
    assert st.burn is None and [n for n, _ in st.toys].count(name) == 0 and len(st.toys) == 2
    st = state("fuse", 96, 1, phase=1, until=99)
    p.ignite(st, st.toys[0][0], 2.0)
    assert st.burn is None

    # 8. sent away: a shout from outside, then they burn each other and everything fades to nothing
    for mood, phase in (("read", 0), ("leave", 1), ("fuse", 1)):
        st = state(mood, 96, 1, who=1, phase=phase, until=99)
        homes = list(st.homes)
        st.cs[1].x = 200  # as if off on a trip
        p.farewell(st, 10.0)
        p.farewell(st, 11.0)  # asking twice changes nothing
        assert (st.mood, st.start) == ("dracarys", 10.0) and (mood == "read" or [c.x for c in st.cs] == homes)
        st.cs[1].x = homes[1]
        px, texts = p.scene(10.5, st, 96, 24, 1, False)
        assert [txt for _, _, txt, _, _ in texts] == ["DRACARYS!"] and not any(c in p.FIRE for row in px for c in row)
        px, texts = p.scene(10.0 + p.HEAR + 0.6, st, 96, 24, 1, False)
        assert not texts and sum(c in p.FIRE for row in px for c in row) > 20
        assert p.ashes(st, 10.5) == 1 > p.ashes(st, 10.0 + p.DRACARYS - 0.5) > p.ashes(st, 10.0 + p.DRACARYS) == 0
        px, _ = p.scene(10.0 + p.DRACARYS, st, 96, 24, 1, False)
        assert not any(c in p.PAL.values() for row in px for c in row)  # no body pixels left, only fire
        assert all(alpha == 0 for *_, alpha in p.toy_spots(10.0 + p.DRACARYS, st, 96, 24))
        x = st.cs[0].x
        p.update(st, 10.0 + p.DRACARYS - 0.1, 1 / 15, 96, 1, cursor=x + 9)
        assert not st.done and st.cs[0].x == x
        p.update(st, 10.0 + p.DRACARYS + 0.1, 1 / 15, 96, 1)
        assert st.done and st.mood == "dracarys"

    # 9. the native widget paints every mood with its toys, and its clickable boxes stay inside the window
    import cairo
    import pixel_claude_gtk as g
    assert set(g.TOYS) == set(p.TOYS)
    cr = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, g.W * g.P, g.H * g.P))
    for mood in [*p.MOODS, "dracarys"]:
        for who in (0, 1):
            for phase in (0, 1):
                for off in (0, g.W + 5):
                    st = state(mood, g.W, 1, who, phase, names=g.TOYS)
                    st.cs[who].x += off
                    p.ignite(st, st.toys[who][0], 1.6)
                    spots = p.toy_spots(2.3, st, g.W, g.H)
                    g.paint(cr, *p.scene(2.3, st, g.W, g.H, 1, sky=False), spots)
                    for _, b in g.toy_boxes(spots):
                        assert 0 <= b.x and b.x + b.width <= g.W * g.P and 0 <= b.y and b.y + b.height <= g.H * g.P
                    assert len(g.boxes(st)) == (1 if off or (mood, phase) == ("fuse", 1) else 2)
                    for b in g.boxes(st):
                        assert 0 <= b.x and b.x + b.width <= g.W * g.P and 0 <= b.y and b.y + b.height <= g.H * g.P
    print("ok")
