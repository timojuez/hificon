import time
from Xlib import X,XK
from Xlib.display import Display
from threading import Thread


class modifier_core(object):
    # Written by Nick Welch in the years 2005-2008.  Author disclaims copyright.

    """caps lock, numlock, and scroll lock make comparing modifiers kind of
    hellish.  it's all contained here."""
    def __init__(self, dpy):
        self.dpy = dpy
        self.nlock = 0
        self.slock = 0
        self.setup_funnylocks()

    def setup_funnylocks(self):
        nlock_key = self.dpy.keysym_to_keycode(XK.string_to_keysym("Num_Lock"))
        slock_key = self.dpy.keysym_to_keycode(XK.string_to_keysym("Scroll_Lock"))
        mapping = self.dpy.get_modifier_mapping()
        mod_names = "Shift Lock Control Mod1 Mod2 Mod3 Mod4 Mod5".split()
        for modname in mod_names:
            index = getattr(X, "%sMapIndex" % modname)
            mask = getattr(X, "%sMask" % modname)
            if nlock_key and nlock_key in mapping[index]:
                self.nlock = mask
            if slock_key and slock_key in mapping[index]:
                self.slock = mask

    def every_lock_combination(self, mask):
        if mask & X.AnyModifier:
            return (X.AnyModifier,)
        clean = mask & ~(X.LockMask | self.nlock | self.slock)
        return (
            clean | X.LockMask,
            clean | X.LockMask | self.nlock,
            clean | X.LockMask | self.nlock | self.slock,
            clean | self.nlock,
            clean | self.nlock | self.slock,
            clean | self.slock,
            clean
        )


class XGrab:
    running = False

    def __init__(self):
        self.display = Display()
        self.root = self.display.screen().root
        self.mods = modifier_core(self.display)
        self.callbacks = {}

    def __enter__(self): self.enter(); return self
    def __exit__(self, *args, **xargs): self.exit()

    def grab_keyname(self, n, *args, **xargs):
        keysym = XK.string_to_keysym(n)
        self.grab_key(keysym, *args, **xargs)

    def ungrab_keyname(self, n, *args, **xargs):
        keysym = XK.string_to_keysym(n)
        self.ungrab_key(keysym, *args, **xargs)

    def grab_key(self, keysym, modifier=None, callback=None):
        keycode = self.display.keysym_to_keycode(keysym)
        modifier = getattr(X, "%sMask" % modifier) if modifier else 0
        for m in self.mods.every_lock_combination(modifier):
            self.root.grab_key(keycode, m, False, X.GrabModeAsync, X.GrabModeAsync)
            self.callbacks[(keycode, m)] = callback

    def ungrab_key(self, keysym):
        keycode = self.display.keysym_to_keycode(keysym)
        self.root.ungrab_key(keycode, X.AnyModifier)

    def grab_button(self, n, modifier=None, callback=None):
        modifier = getattr(X, "%sMask" % modifier) if modifier else 0
        for m in self.mods.every_lock_combination(modifier):
            self.root.grab_button(n, m, False, X.ButtonPressMask|X.ButtonReleaseMask,
                X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE)
            self.callbacks[(n, m)] = callback

    def ungrab_button(self, n):
        self.root.ungrab_button(n, X.AnyModifier)

    def mainloop(self):
        while self.running:
            if self.display.pending_events():
                event = self.display.next_event()
                try:
                    pressed = event.type in (X.KeyPress, X.ButtonPress)
                    callback = self.callbacks.get((event.detail, event.state), None)
                except AttributeError: pass
                else:
                    if callback: callback(pressed, event)
            else: time.sleep(.1)

    def enter(self):
        self.running = True
        Thread(target=self.mainloop, daemon=True, name="x11_grab").start()

    def exit(self):
        self.running = False

