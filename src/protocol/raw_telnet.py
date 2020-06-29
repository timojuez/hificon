from ..amp import Feature, TelnetAmp, make_amp


class _Amp(TelnetAmp):
    """ Low level amp """
    protocol = "Raw_telnet"
    
    def query(self, cmd, matches=None):
        """
        send @cmd to amp and return line where matches(line) is True
        """
        if not matches: return self.send(cmd)
        class RawFeature(Feature):
            call = cmd
            matches = lambda self, data: matches(data)
            def decode(self, cmd): return cmd
            def encode(self, value): return value
        RawFeature.__name__ = cmd
        return RawFeature(self).get()

Amp = make_amp({}, _Amp)
