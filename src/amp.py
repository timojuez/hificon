"""
Common abstract amplifier classes for creating an amp scheme.
Examples in src/schemes
"""

from .core.util import log_call
from .core import config, AbstractScheme, TelnetScheme, features


class AbstractAmp(AbstractScheme): pass

class TelnetAmp(AbstractAmp, TelnetScheme): pass

@AbstractAmp.add_feature
class Power(features.ConstantValueMixin, features.BoolFeature): pass

@AbstractAmp.add_feature
class Source(features.ConstantValueMixin, features.SelectFeature): pass

@AbstractAmp.add_feature
class Volume(features.ConstantValueMixin, features.DecimalFeature): pass

@AbstractAmp.add_feature
class Muted(features.ConstantValueMixin, features.BoolFeature): pass

@AbstractAmp.add_feature
class IsPlaying(features.ConstantValueMixin, features.BoolFeature): pass

