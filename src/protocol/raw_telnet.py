from ..core import features, TelnetProtocol


class RawTelnet(TelnetProtocol):
    """ Low level target """
    description = "Reads telnet data without further interpretation"
    protocol = "raw_telnet"
    uri_client = f"{protocol}://IP:PORT"
    
    def query(self, cmd, matches=None):
        """
        send @cmd to target and return line where matches(line) is True
        """
        if not matches: return self.send(cmd)
        class RawFeature(features.Feature):
            key = None
            call = cmd
            matches = lambda self, data: matches(data)
            def decode(self, cmd): return cmd
            def encode(self, value): return value
        RawFeature.__name__ = cmd
        f = RawFeature(self)
        f.wait_poll(force=True)
        return f.get()

