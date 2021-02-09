"""
Connects system events to a target.
Main class AmpController
"""

from ..core.util.system_events import SystemEvents
from ..core.util import log_call
from ..core import config


class _Base(SystemEvents):

    def __init__(self, target, *args, **xargs):
        self.verbose = xargs.get("verbose",0)
        self.target = target
        self.target.preload_features.update((config.source, config.power))
        super().__init__(*args, **xargs)

    def poweron(self): self.target.schedule(self._poweron, requires=(config.power, config.source))

    def _poweron(self):
        if getattr(self.target, config.power): return
        if config["Amp"].get("source"): self.target.features[config.source].send(config.getlist("Amp","source")[0])
        setattr(self.target, config.power, True)

    can_poweroff = property(
        lambda self: getattr(self.target,config.power)
        and (not config["Amp"]["source"] or getattr(self.target,config.source) in config.getlist("Amp","source")))

    def poweroff(self, force=False):
        self.target.schedule(lambda:(force or self.can_poweroff) and setattr(self.target,config.power,False),
            requires=(config.power, config.source))


class SoundMixin(_Base):
    """ call target.on_start_playing and target.on_stop_playing when pulse decides """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.bind(on_connect=self.on_target_connect)

    @log_call
    def on_start_playing(self): self.target.on_start_playing()

    @log_call
    def on_stop_playing(self): self.target.on_stop_playing()
    
    def on_target_connect(self):
        if hasattr(self,"pulse") and self.pulse.connected and self.pulse.is_playing:
            self.on_start_playing()

    
class KeepConnected(_Base):
    """ keep target connected whenever possible """

    @log_call
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        self.target.exit()
        self.exit()
        
    @log_call
    def on_suspend(self):
        super().on_suspend()
        self.target.exit()

    @log_call
    def on_resume(self):
        """ Is being executed after resume computer from suspension """
        self.target.enter()
        super().on_resume()


class AutoPower(_Base):
    """ implementing actions for automatic power management """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.bind(on_start_playing = self.poweron)
        self.target.bind(on_idle = self.on_target_idle)
    
    def on_target_idle(self): self.target.poweroff()

    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        self.poweroff()
        super().on_shutdown(sig,frame)
        
    def on_suspend(self):
        self.poweroff()
        super().on_suspend()


class AmpController(AutoPower, KeepConnected, SoundMixin, _Base):
    """
    Adds system events listener. Keep target connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    pass

