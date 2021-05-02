from ..core.util import log_call
from ..core import config
from ..core.target_controller import TargetController


class SoundMixin:
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


class AutoPower:
    """ implementing actions for automatic power management when amp starts/stop playing """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.bind(on_start_playing = self.poweron)
        self.target.bind(on_idle = self.on_target_idle)
    
    def on_target_idle(self): self.target.poweroff()


class AmpController(AutoPower, SoundMixin, TargetController):
    """
    Adds system events listener. Keep target connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.preload_features.update((config.source, config.power))

    def poweron(self): self.target.schedule(self._poweron, requires=(config.power, config.source))

    def _poweron(self):
        if getattr(self.target, config.power): return
        if config["Amp"].get("source"):
            self.target.features[config.source].remote_set(config.getlist("Amp","source")[0])
        setattr(self.target, config.power, True)

    can_poweroff = property(
        lambda self: getattr(self.target,config.power)
        and (not config["Amp"]["source"] or getattr(self.target,config.source) in config.getlist("Amp","source")))

    def poweroff(self, force=False):
        self.target.schedule(lambda:(force or self.can_poweroff) and setattr(self.target,config.power,False),
            requires=(config.power, config.source))


