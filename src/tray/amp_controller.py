"""
Connects system events to the amp.
Main class AmpController
"""

from ..util.system_events import SystemEvents
from ..util import log_call
from ..config import config


class _Base:

    def __init__(self, amp, *args, **xargs):
        self.verbose = xargs.get("verbose",0)
        self.amp = amp
        super().__init__(*args, **xargs)


class SoundMixin:
    """ call amp.on_start_playing and amp.on_stop_playing when pulse decides """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp.bind(on_connect=self.on_amp_connect)

    @log_call
    def on_start_playing(self): self.amp.on_start_playing()

    @log_call
    def on_stop_playing(self): self.amp.on_stop_playing()
    
    def on_amp_connect(self):
        if hasattr(self,"pulse") and self.pulse.connected and self.pulse.is_playing:
            self.on_start_playing()

    
class KeepConnected:
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
        self.amp.bind(on_start_playing = self.amp.poweron)
        #self.amp.bind(on_idle = self.amp.poweroff)
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        self.amp.poweroff()
        super().on_shutdown(sig,frame)
        
    def on_suspend(self):
        self.amp.poweroff()
        super().on_suspend()


class AmpController(AutoPower, KeepConnected, SoundMixin, _Base, SystemEvents):
    """
    Adds system events listener. Keep amp connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    pass

