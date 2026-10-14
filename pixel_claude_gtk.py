#!/usr/bin/env python3
"""Pixel Claude as a native desktop widget (GTK4 + layer shell), bottom-right of the screen.

Clicks pass through everywhere except on the creatures and toys. Put the mouse on a creature and it
scurries off while the widget turns see-through; put it on a toy and one of them firebends it away.
Click a creature to say hi.
Run: python3 pixel_claude_gtk.py [SIZE]   (SIZE: screen pixels per art pixel, default 6)
Send away with a finale: send it SIGUSR1.    Stop at once: pkill -f pixel_claude_gtk
~/.local/bin/summon_beasts and ~/.local/bin/send_away wrap the first two.
"""
import signal
import sys
import time
from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")  # has to load before GTK pulls in libwayland, or layer shell does not work

import cairo
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell as Layer

import pixel_claude as core

W, H = 96, 24  # grid width and height in art pixels
P = int(sys.argv[1]) if sys.argv[1:] and sys.argv[1].isdigit() else 6  # screen pixels per art pixel
MARGIN_BOTTOM = 60  # ponytail: a guess that clears a dock or status bar; adjust to taste


def image(px):
    """A grid of RGB tuples (None = transparent) as a cairo surface, one pixel per cell."""
    data = bytearray()  # ARGB32 is B, G, R, A in memory
    for row in px:
        for c in row:
            data += bytes((c[2], c[1], c[0], 255)) if c else b"\0\0\0\0"
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, len(px[0]), len(px))


TOYS = {name: image([[pal.get(ch) for ch in row] for row in grid]) for name, (grid, pal) in core.TOYS.items()}


def boxes(st):
    """Screen rectangles of the creatures (chair and hover headroom included): the only clickable area."""
    if st.mood == "fuse" and st.phase == 1:  # one double-size creature where they met
        x0 = max(0, int(sum(st.homes) / 2) - 9)
        return [cairo.RectangleInt(x0 * P, 0, min(36, W - x0) * P, H * P)]
    out = []
    for c in st.cs:
        x0, x1 = max(0, int(c.x)), min(W, int(c.x) + 18)
        if x1 > x0:  # skipped while it is off the screen
            out.append(cairo.RectangleInt(x0 * P, (H - 16) * P, (x1 - x0) * P, 16 * P))
    return out


def toy_boxes(spots):
    """(name, screen rectangle) of each toy that is at least partly inside the window."""
    out = []
    for name, x, y, *_ in spots:
        x0, y0 = max(0, round(x * P)), max(0, round(y * P))
        x1, y1 = min(W * P, round(x * P) + core.TOY * P), min(H * P, round(y * P) + core.TOY * P)
        if x1 > x0 and y1 > y0:
            out.append((name, cairo.RectangleInt(x0, y0, x1 - x0, y1 - y0)))
    return out


def inside(box, mouse):
    return box.x <= mouse[0] < box.x + box.width and box.y <= mouse[1] < box.y + box.height


def stamp(cr, img, x, y, scale, alpha=1):
    cr.save()
    cr.translate(round(x * P), round(y * P))
    cr.scale(scale, scale)
    cr.set_source_surface(img, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_NEAREST)  # keep the pixels crisp
    cr.paint_with_alpha(alpha)
    cr.restore()


def paint(cr, px, texts, spots=()):
    """spots: core.toy_spots(); toys go behind the creatures unless flagged in front."""
    art = image(px)
    for layer in (False, None, True):  # toys behind, the pixel art, toys in front
        if layer is None:
            stamp(cr, art, 0, 0, P)
        for name, x, y, front, alpha in spots:
            if front is layer:
                stamp(cr, TOYS[name], x, y, core.TOY * P / TOYS[name].get_width(), alpha)

    # text keeps the terminal grid (one art pixel wide, two tall per character) so balloons still fit it
    cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(100)
    cr.set_font_size(100 * P / cr.text_extents("M").x_advance)
    ascent, descent = cr.font_extents()[:2]
    for col, row, txt, fg, _ in texts:
        col = max(0, min(col, len(px[0]) - len(txt)))
        cr.set_source_rgb(*(v / 255 for v in fg))
        for i, ch in enumerate(txt):
            cr.move_to((col + i) * P, row * 2 * P + (2 * P - ascent - descent) / 2 + ascent)
            cr.show_text(ch)


def activate(app):
    if app.get_windows():  # already running
        return
    if not Layer.is_supported():
        sys.exit("pixel_claude_gtk needs a Wayland compositor with the layer-shell protocol")
    st, t0, frame = core.new_state(TOYS), time.monotonic(), []
    clock, pointer = [t0], [None]  # pointer: the mouse position in screen pixels while it is on one of them or a toy

    win = Gtk.Window(application=app, decorated=False)
    Layer.init_for_window(win)
    Layer.set_namespace(win, "pixel-claude")
    Layer.set_layer(win, Layer.Layer.TOP)
    Layer.set_anchor(win, Layer.Edge.BOTTOM, True)
    Layer.set_anchor(win, Layer.Edge.RIGHT, True)  # flush right: that edge is where they walk off the monitor
    Layer.set_margin(win, Layer.Edge.BOTTOM, MARGIN_BOTTOM)
    Layer.set_keyboard_mode(win, Layer.KeyboardMode.NONE)
    css = Gtk.CssProvider()
    css.load_from_string("window { background: transparent; }")
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    area = Gtk.DrawingArea(content_width=W * P, content_height=H * P)
    area.set_draw_func(lambda _area, cr, _w, _h: frame and paint(cr, *frame))
    win.set_child(area)

    def tick():
        now = time.monotonic()
        t, mouse = now - t0, pointer[0]
        toys = toy_boxes(core.toy_spots(t, st, W, H))
        on_creature = mouse is not None and any(inside(b, mouse) for b in boxes(st))
        for name, box in toys if mouse else ():
            if inside(box, mouse):
                core.ignite(st, name, t)  # mouse on a toy: it gets burnt out of the way
        if mouse and not on_creature and not any(inside(box, mouse) for _, box in toys):
            pointer[0] = None  # they got clear of a still mouse, and no leave event comes until the mouse moves
        core.update(st, t, now - clock[0], W, 1, mouse[0] / P if on_creature else None)
        clock[0] = now
        if st.done:  # sent away and burnt out
            app.quit()
            return False
        frame[:] = [*core.scene(t, st, W, H, 1, sky=False), core.toy_spots(t, st, W, H)]
        surface = win.get_surface()
        if surface:  # every frame, since GTK resets the region when it re-allocates the window
            surface.set_input_region(cairo.Region(boxes(st) + [box for _, box in toys]))
        area.set_opacity(0.2 if on_creature else 1)  # see-through while the mouse is on one of them
        area.queue_draw()
        return True

    def clicked(_gesture, _n, x, _y):
        for i, c in enumerate(st.cs):
            if int(c.x) * P <= x < (int(c.x) + 18) * P:
                core.greet(st, i, time.monotonic() - t0)

    click, hover = Gtk.GestureClick(), Gtk.EventControllerMotion()
    click.connect("pressed", clicked)
    hover.connect("motion", lambda _c, x, y: pointer.__setitem__(0, (x, y)))
    hover.connect("leave", lambda _c: pointer.__setitem__(0, None))
    area.add_controller(click)
    area.add_controller(hover)
    GLib.timeout_add(66, tick)
    # send_away sends SIGUSR1: play the finale, then tick() quits
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: core.farewell(st, time.monotonic() - t0) or True)
    win.present()


if __name__ == "__main__":
    app = Gtk.Application(application_id="local.pixel.claude")
    app.connect("activate", activate)
    app.run(None)
