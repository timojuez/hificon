"""
Connects system events to a target. Can do automatic reconnects and bind computer power to device power.
Main class: TargetController
"""

from .util.system_events import SystemEvents
from .util import log_call


class _Base(SystemEvents):

    def __init__(self, target, *args, **xargs):
        self.verbose = xargs.get("verbose",0)
        self.target = target
        super().__init__(*args, **xargs)

    def poweron(self): pass

    def poweroff(self): pass


class AutoConnect(_Base):
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
    """ Power off target when computer shuts down or suspends """

    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        self.poweroff()
        super().on_shutdown(sig,frame)
        
    def on_suspend(self):
        self.poweroff()
        super().on_suspend()


class TargetController(AutoPower, AutoConnect, _Base):
    """
    Adds system events listener. Keep target connected whenever possible
    Features: Auto power, auto reconnecting, 
    """
    pass

