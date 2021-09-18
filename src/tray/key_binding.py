# -*- coding: utf-8 -*-
import time, sys, tempfile, os
from threading import Thread, Lock, Event
from decimal import Decimal
from contextlib import suppress
from ..core import config
from ..info import PKG_NAME
from pynput import mouse, keyboard


MAX_VOL_CHANGE = config.getint("Hotkeys", "mouse_max_volume_step")


class VolumeChanger:
    """ Mixin class for managing volume up/down hot keys and mouse gesture """
    _new_vol = None
    _volume_ref = None
    _y_ref = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.interval = config.getfloat("Hotkeys","interval")/1000
        self.step = config.getdecimal("Hotkeys","step")
        self._volume_changed = Event()
        self._volume_step = Event()
        self._set_volume_lock = Lock()
        self.target.preload_features.add(config.volume)
        self.target.features[config.volume].bind(
            on_change = self.on_volume_change,
            on_send = self._volume_changed.clear)
        Thread(target=self.volume_thread, daemon=True, name="key_binding").start()

    def on_volume_change(self, val):
        """ target volume changed """
        #self.set_volume_reference(self._y, val)
        self._volume_changed.set()

    def set_volume_reference(self, y, vol):
        """ link a y-coordinate to a volume value """
        self._y_ref, self._volume_ref = y, vol

    def on_mouse_down(self, x, y):
        try: self.set_volume_reference(y, self.target.features[config.volume].get())
        except ConnectionError: pass
        self._new_vol = None
        if self.interval: time.sleep(self.interval)

    def on_mouse_up(self, x, y):
        self._volume_ref = None
        #Thread(target=self.poweron, args=(True,), name="poweron", daemon=True).start()

    def on_mouse_move(self, x, y):
        if self._volume_ref is not None:
            vol = self.target.features[config.volume]
            new_vol = self._volume_ref-int((y-self._y_ref)*config.getdecimal("Hotkeys", "mouse_sensitivity"))
            vol_max = min(vol.max, vol.get()+MAX_VOL_CHANGE)
            vol_min = vol.min
            if new_vol > vol_max or new_vol < vol_min:
                # mouse has been moved to an illegal point
                new_vol = max(vol_min, min(vol_max, new_vol))
                self.set_volume_reference(y, new_vol)
            self.set_volume(new_vol)

    def set_volume(self, volume):
        with self._set_volume_lock:
            self._new_vol = volume
            self._volume_step.set()

    def on_volume_key_press(self, button):
        self.target.schedule(
            lambda:self.set_volume(getattr(self.target, config.volume) + self.step*(int(button)*2-1)),
            requires=(config.volume,))

    def on_mute_key_press(self):
        self.target.schedule(
            lambda:setattr(self.target, config.muted, not getattr(self.target, config.muted)),
            requires=(config.muted,))

    def volume_thread(self):
        while True:
            self._volume_step.wait()
            self.target.schedule(self.step_volume, requires=(config.volume,))
    
    def step_volume(self):
        with self._set_volume_lock:
            self._volume_step.clear()
            new_vol = self._new_vol
            self._new_vol = None
        if new_vol is not None:
            volume = self.target.features[config.volume]
            new_vol = max(min(new_vol, volume.max), volume.min)
            if new_vol != volume.get():
                volume.remote_set(new_vol)
                if self.interval: time.sleep(self.interval)
                self._volume_changed.wait(.2) # wait for on_feature_change


class InputDeviceListener:
    """ Runs the pynput listeners """
    _pressed = False
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_move=self._on_mouse_move,
        )
        self.key_listener = keyboard.Listener(
            on_press=self.on_hotkey_press,
        )

    def __enter__(self): self.enter(); return self
    def __exit__(self, *args, **xargs): self.exit()

    def enter(self):
        self.mouse_listener.start()
        self.key_listener.start()

    def exit(self):
        self.mouse_listener.stop()
        self.key_listener.stop()

    def on_mouse_click(self, x, y, button, pressed):
        if button != getattr(mouse.Button, config["Hotkeys"]["mouse_button"], None): return
        self._pressed = pressed
        if pressed: self.on_mouse_down(x, y)
        else: self.on_mouse_up(x, y)

    def _on_mouse_move(self, x, y):
        if self._pressed: self.on_mouse_move(x, y)

    def on_hotkey_press(self, key):
        if not self.config["volume_hotkeys"]: return
        if key == keyboard.Key.media_volume_up: self.on_volume_key_press(True)
        elif key == keyboard.Key.media_volume_down: self.on_volume_key_press(False)
        elif key == keyboard.Key.media_volume_mute: self.on_mute_key_press()


class KeyBinding(VolumeChanger, InputDeviceListener): pass

