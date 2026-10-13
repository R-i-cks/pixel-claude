"""Self-check for pixel_claude.py: python3 pixel_claude_check.py"""
import pixel_claude as p
from types import SimpleNamespace as NS


def state(mood, w, s, who=0, phase=0, until=8.0, xa=None, xb=None, line=p.THOUGHTS[1]):
    span = max(0, w - 18 * s)
    return NS(cs=[NS(x=max(0, span / 2 - 12 * s) if xa is None else xa, d=1),
                  NS(x=max(0, span / 2 + 12 * s) if xb is None else xb, d=-1)],
              mood=mood, who=who, phase=phase, mark=1.0, home=0.0, start=0.0, until=until, line=line)


if __name__ == "__main__":
    # 1. every mood x size x mode x actor x phase x time renders with the right shape
    for sky in (True, False):
        for w, rows in [(100, 30), (200, 60), (64, 12), (42, 12), (10, 3), (1, 3)]:
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
                                for col, row, txt, fg, bg in texts:  # balloon text sits on balloon pixels
                                    if mood in ("think", "wave") and w >= 42:
                                        assert 0 <= col and col + len(txt) <= w and px[row * 2][col] == p.CREAM, (mood, w, col)

    # 2. long simulated runs: every mood reached, bounds and left/right order hold, flowers get
    #    handed over, whoever leaves the screen comes back home, calm moods dominate
    for w, s in [(64, 1), (100, 2), (200, 4)]:
        st = NS(cs=[NS(x=None, d=1), NS(x=None, d=-1)], mood="idle", who=0, phase=0, mark=0.0, home=0.0,
                start=0.0, until=0.0, line="")
        t, seen, gave, left, calm, span, n = 0, set(), 0, 0, 0, w - 18 * s, 120000
        for _ in range(n):
            t += 1 / 15
            was, began = (st.mood, st.phase), st.start
            p.update(st, t, 1 / 15, w, s)
            seen.add(st.mood)
            calm += st.mood in p.STILL or st.mood == "idle"
            gave += st.mood == "flowers" and st.phase == 1 and was == ("flowers", 0)
            left += st.mood == "leave" and st.phase == 1 and was == ("leave", 0)
            if st.start != began and was[0] == "leave":
                assert was[1] == 3, was  # a trip is never abandoned half way
            a, b = st.cs
            away = st.mood == "leave" and st.phase < 3
            for c in st.cs:
                assert away and c is st.cs[st.who] or 0 <= c.x <= span, (st.mood, st.phase, c.x)
            assert away or a.x < b.x, (st.mood, a.x, b.x)
            assert st.until - st.start < 121
            p.scene(t, st, w, 24 * s, s, False)
        assert seen == set(p.MOODS), seen
        assert gave and left and calm / n > 0.8, (gave, left, calm / n)
        print(f"{w} cols, scale {s}: all moods reached, {gave} flowers, {left} trips off-screen, {calm / n:.0%} of the time calm")
    print("ok")
