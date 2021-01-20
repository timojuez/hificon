"""
Common abstract amplifier classes for creating an amp protocol.
Examples in src/protocol
"""

from threading import Timer, Lock
from ..util import log_call
from ..common import config, AbstractProtocol, AbstractTelnetProtocol


class AbstractAmp(AbstractProtocol):
    """ provide on_start_playing, on_stop_playing, on_idle, on_poweron and on_poweroff """
    _soundMixinLock = Lock()
    _idle_timer = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        if config.power in self.features: self.features[config.power].bind(
            lambda val:self.on_poweron() if val else self.on_poweroff())

    @log_call
    def on_start_playing(self):
        if self._idle_timer: self._idle_timer.cancel()

    @log_call
    def on_stop_playing(self):
        with self._soundMixinLock:
            if self._idle_timer and self._idle_timer.is_alive(): return
            try: timeout = config.getfloat("Amp","poweroff_after")*60
            except ValueError: return
            if not timeout: return
            self._idle_timer = Timer(timeout, self.on_idle)
            self._idle_timer.start()
    
    @log_call
    def on_idle(self): pass

    @log_call
    def on_poweron(self): pass
    
    @log_call
    def on_poweroff(self):
        if self._idle_timer: self._idle_timer.cancel()


class TelnetAmp(AbstractAmp, AbstractTelnetProtocol): pass


