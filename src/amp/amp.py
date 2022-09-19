"""
Common abstract amplifier classes for creating an amp scheme.
Examples in src/schemes
"""

from ..core.util import log_call
from ..core import config, AbstractScheme, TelnetScheme, features


class AbstractAmp(AbstractScheme):
    """ provide on_start_playing, on_stop_playing """
    _playing = False

    @log_call
    def on_start_playing(self): self._playing = True

    @log_call
    def on_stop_playing(self): self._playing = False


class TelnetAmp(AbstractAmp, TelnetScheme): pass

@AbstractAmp.add_feature
class Power(features.ConstantValueMixin, features.BoolFeature): pass

@AbstractAmp.add_feature
class Source(features.ConstantValueMixin, features.SelectFeature): pass

@AbstractAmp.add_feature
class Volume(features.ConstantValueMixin, features.DecimalFeature): pass

@AbstractAmp.add_feature
class Muted(features.ConstantValueMixin, features.BoolFeature): pass

