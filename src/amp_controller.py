"""
Connects system events to the amp.
Main class AmpController
"""

from threading import Timer, Lock
from .util.function_bind import Autobind
from .util.system_events import SystemEvents
from .util import log_call
from .config import config


class _Verbosity(object):
    
    def __init__(self, *args, **xargs):
        self.verbose = xargs.get("verbose",0)
        super().__init__(*args,**xargs)


class AmpEvents(Autobind):
    
    def __init__(self, obj, *args, **xargs):
        super().__init__(obj, *args, **xargs)
        self.amp = obj

    
class SoundMixin(AmpEvents,_Verbosity):
    """ provide on_amp_idle and may call on_start_playing when connected """
    _soundMixinLock = Lock()

    def on_feature_change(self, key, value, *args): # bound to self.amp by Autobind
        super().on_feature_change(key, value, *args)
        if key == "input_signal" and value == True: self.on_start_playing()
        elif key == "input_signal" and value == False: self.on_stop_playing()

    @log_call
    def on_start_playing(self):
        if hasattr(self,"_idle_timer"): self._idle_timer.cancel()
        super().on_start_playing()

    @log_call
    def on_stop_playing(self):
        super().on_stop_playing()
        with self._soundMixinLock:
            if hasattr(self,"_idle_timer") and self._idle_timer.is_alive(): return
            try: timeout = config.getfloat("Amp","poweroff_after")*60
            except ValueError: return
            if not timeout: return
            self._idle_timer = Timer(timeout, self.on_amp_idle)
            self._idle_timer.start()
    
    @log_call
    def on_amp_idle(self): pass

    def on_poweroff(self): # bound to self.amp by Autobind
        if hasattr(self,"_idle_timer"): self._idle_timer.cancel()

    def on_connect(self): # bound to self.amp by Autobind
        super().on_connect()
        if hasattr(self,"pulse") and self.pulse.connected and self.pulse.is_playing:
            self.on_start_playing()

    
class KeepConnected(_Verbosity):
    """ keep amp connected whenever possible """

    @log_call
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        super().on_shutdown(sig,frame)
        self.amp.exit()
        
    @log_call
    def on_suspend(self):
        super().on_suspend()
        self.amp.exit()

    @log_call
    def on_resume(self):
        """ Is being executed after resume computer from suspension """
        self.amp.enter()
        super().on_resume()


class AutoPower:
    """ implementing actions for automatic power management """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp.preload_features.update((config.source, config.power))
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        self.amp.poweroff()
        super().on_shutdown(sig,frame)
        
    def on_suspend(self):
        self.amp.poweroff()
        super().on_suspend()
    
    def on_start_playing(self):
        super().on_start_playing()
        self.amp.poweron()

    def on_amp_idle(self):
        super().on_amp_idle()
        self.amp.poweroff()


class AmpController(AutoPower, KeepConnected, SoundMixin, SystemEvents):
    """
    Adds system events listener. Keep amp connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    pass

