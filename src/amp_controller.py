"""
Connects system events to the amp.
Main class AmpController
"""

from threading import Timer
from .util.function_bind import Autobind
from .util.system_events import SystemEvents
from .util import log_call
from .config import config


class AmpEvents(Autobind):
    
    def __init__(self, obj):
        super().__init__(obj)
        self.amp = obj

    
class SoundMixin(AmpEvents):
    """ provide on_sound_idle and may call on_start_playing when connected """

    @log_call
    def on_start_playing(self):
        if hasattr(self,"_timer_poweroff"): self._timer_poweroff.cancel()
        super().on_start_playing()

    @log_call
    def on_stop_playing(self):
        super().on_stop_playing()
        try: timeout = config.getfloat("Amp","poweroff_timeout")*60
        except ValueError: return
        if not timeout: return
        self._timer_poweroff = Timer(timeout,self.on_sound_idle)
        self._timer_poweroff.start()
    
    @log_call
    def on_sound_idle(self): pass

    def on_connect(self):
        super().on_connect()
        if hasattr(self,"pulse") and self.pulse.connected and self.pulse.is_playing:
            self.on_start_playing()

    
class KeepConnected:
    """ keep amp connected whenever possible """
    
    def mainloop(self):
        self.amp.enter()
        super().mainloop()
    
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

    def on_sound_idle(self):
        super().on_sound_idle()
        self.amp.poweroff()
    

class AmpController(AutoPower, KeepConnected, SoundMixin, SystemEvents):
    """
    Adds system events listener. Keep amp connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    pass
