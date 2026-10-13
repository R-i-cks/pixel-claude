"""Self-check for pixel_claude.py: python3 pixel_claude_check.py"""

import pixel_claude as p
from types import SimpleNamespace as NS

def state(mood, w, s, who=0, given=None, until=8.0, xa=None, xb=None, line=p.THOUGHTS[1]):
    span = max(0, w - 18 * s)
    return NS(cs=[NS(x=span / 2 - 12 * s if xa is None else xa, d=1), NS(x=span / 2 + 12 * s if xb is None else xb, d=-1)],
              mood=mood, who=who, given=given, moved=False, start=0.0, until=until, line=line)

# 1. every mood x size x mode x actor x time renders with the right shape
for sky in (True, False):
    for w, rows in [(100, 30), (200, 60), (64, 12), (42, 12), (10, 3), (1, 3)]:
        s = max(1, min(4, w // 48, rows // 11))
        for mood in p.MOODS:
            for who in (0, 1):
                for given in (None, 1.0):
                    for t in [0, 0.1, 0.5, 1.3, 2.9, 4.2, 5.5, 7.6, 7.99]:
                        st = state(mood, w, s, who, given)
                        px, texts = p.scene(t, st, w, rows * 2, s, sky)
                        assert len(px) == rows * 2 and all(len(r) == w for r in px)
                        assert p.draw(px, texts).count('\n') == rows - 1
                        for col, row, txt, fg, bg in texts:  # balloon text always sits on balloon pixels
                            if mood in ("think", "wave", "vanish") and w >= 42:
                                assert 0 <= col and col + len(txt) <= w and px[row * 2][col] == p.CREAM, (mood, w, col, row)

# 2. long simulated run: every mood reached, order and bounds hold, flowers get given
for w, s in [(64, 1), (100, 2), (200, 4)]:
    st = NS(cs=[NS(x=None, d=1), NS(x=None, d=-1)], mood="idle", who=0, given=None, moved=False, start=0.0, until=0.0, line="")
    t, seen, gave, span = 0, set(), 0, w - 18 * s
    for _ in range(60000):
        t += 1 / 15
        prev = st.given
        p.update(st, t, 1 / 15, w, s)
        seen.add(st.mood)
        gave += bool(st.given and not prev)
        a, b = st.cs
        assert 0 <= a.x <= span and 0 <= b.x <= span and a.x < b.x, (st.mood, a.x, b.x)
        assert st.until - st.start < 61
        p.scene(t, st, w, 24 * s, s, False)
    assert seen == set(p.MOODS), seen
    print(w, s, "all moods reached, flowers given", gave, "times")

print("ok")
