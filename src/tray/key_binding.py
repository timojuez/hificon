# -*- coding: utf-8 -*-
import time, sys, tempfile, os
from threading import Thread, Lock, Event
from decimal import Decimal
from contextlib import suppress
from ..info import PKG_NAME
from .common import config
from pynput import mouse, keyboard
LINUX = sys.platform == "linux"
if LINUX: from ..core.util.x11_grab import XGrab


MAX_VOL_CHANGE = config["hotkeys"]["mouse_max_volume_step"]


class VolumeChanger:
    """ Mixin class for managing volume up/down hot keys and mouse gesture """
    _new_vol = None
    _volume_ref = None
    _y_ref = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.interval = config["hotkeys"]["interval"]/1000
        self.step = config["hotkeys"]["step"]
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
        self._new_vol = None
        try: self.set_volume_reference(y, self.target.features[config.volume].get())
        except ConnectionError: pass
        if self.interval: time.sleep(self.interval)

    def on_mouse_up(self, x, y):
        self._volume_ref = None
        #Thread(target=self.poweron, args=(True,), name="poweron", daemon=True).start()

    def on_activated_mouse_move(self, x, y):
        self.target.schedule(lambda:self._on_activated_mouse_move(x,y), requires=(config.volume,))

    def _on_activated_mouse_move(self, x, y):
        if self._volume_ref is not None:
            vol = self.target.features[config.volume]
            new_vol = self._volume_ref-int((y-self._y_ref)*config["hotkeys"]["mouse_sensitivity"])
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
            lambda:self.set_volume(self.target.features[config.volume].get() + self.step*(int(button)*2-1)),
            requires=(config.volume,))

    def on_mute_key_press(self):
        self.target.schedule(
            lambda:self.target.features[config.muted].remote_set(not self.target.features[config.muted].get()),
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
        self._ctrl = False
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_move=self.on_mouse_move,
        )
        self.key_listener = keyboard.Listener(
            on_press=self.on_hotkey_press,
            on_release=self.on_hotkey_release,
        )
        self._config_button = config["hotkeys"]["mouse_button"]
        if LINUX: self._xgrab = XGrab()
        self._controller = keyboard.Controller()

    def __enter__(self):
        self.mouse_listener.start()
        self.key_listener.start()
        self.set_key_grabbing(config["hotkeys"]["volume_hotkeys"])
        self.set_button_grabbing(bool(self._config_button))
        if LINUX: self._xgrab.enter()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        self.mouse_listener.stop()
        self.key_listener.stop()
        self.set_key_grabbing(False)
        self.set_button_grabbing(False)
        if LINUX: self._xgrab.exit()

    def on_mouse_click(self, x, y, button, pressed):
        if button.name != self._config_button: return
        self._pressed = pressed
        if pressed: self.on_mouse_down(x, y)
        else: self.on_mouse_up(x, y)

    def on_mouse_move(self, x, y):
        if self._pressed: self.on_activated_mouse_move(x, y)

    def on_hotkey_press(self, key):
        if not config["hotkeys"]["volume_hotkeys"]: return
        key = self.key_listener.canonical(key)
        if key == keyboard.Key.ctrl: self._ctrl = True
        elif not self._ctrl: return
        elif key == keyboard.Key.media_volume_up: self.on_volume_key_press(True)
        elif key == keyboard.Key.media_volume_down: self.on_volume_key_press(False)
        elif key == keyboard.Key.media_volume_mute: self.on_mute_key_press()

    def on_hotkey_release(self, key):
        key = self.key_listener.canonical(key)
        if key == keyboard.Key.ctrl: self._ctrl = False

    def set_keyboard_media_keys(self, *args, **xargs):
        self.set_key_grabbing(False)
        super().set_keyboard_media_keys(*args, **xargs)
        self.set_key_grabbing(config["hotkeys"]["volume_hotkeys"])

    def set_key_grabbing(self, value):
        """ stop forwarding volume media buttons to other programs """
        if not LINUX: return
        for key in [keyboard.Key.media_volume_up, keyboard.Key.media_volume_up, keyboard.Key.media_volume_mute]:
            if value: self._xgrab.grab_key(key.value.vk, "Control")
            else: self._xgrab.ungrab_key(key.value.vk)

    def set_mouse_key(self, key):
        self.set_button_grabbing(False)
        self._config_button = key
        super().set_mouse_key(key)
        self.set_button_grabbing(bool(self._config_button))

    def set_button_grabbing(self, value):
        """ stop forwarding configured mouse button events to other programs """
        if not LINUX or not self._config_button: return
        button_int = getattr(mouse.Button, self._config_button).value
        if value: self._xgrab.grab_button(button_int)
        else: self._xgrab.ungrab_button(button_int)


class KeyBinding(VolumeChanger, InputDeviceListener): pass

