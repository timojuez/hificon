import argparse, time, sys, os
from .core.transport.features import NumericFeature
from . import Target


class Main:
    
    def __init__(self):
        script = os.path.basename(__file__)
        parser = argparse.ArgumentParser(description=f'Tool for creating a HiFi script for HiFiSh. It can record target changes to repeat the actions later by calling the HiFi script. Writes to stdout. Example: {script} > batch.hifi && hifish batch.hifi')
        parser.add_argument('-a', '--all', action="store_true", help='Include all current feature values, not just recorded ones')
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument("--relative", action="store_true", help="For numeric values, denote only the difference instead of absolute value")
        group.add_argument("-r", "--raw", action="store_true", help="Use low level commands")
        parser.add_argument("--debug", action="store_true", help="Same as -ar")
        parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
        parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
        args = parser.parse_args()
        assert(not(args.all and args.relative))
        self.all_features = args.all or args.debug
        self.raw = args.raw or args.debug
        self.relative = args.relative
        with Target(args.target, verbose=args.verbose) as self.t:
            self.append("#!/usr/bin/env hifish")
            self.append("#")
            self.append(f"# CREATED WITH {script}")
            self.append("#")
            self.append()
            if self.all_features:
                self.start_recording()
                for call in set([f.call for f in self.t.features.values() if f.call]):
                    self.t.send(call)
                    time.sleep(.2)
                time.sleep(3)
            else:
                if self.relative:
                    [f.async_poll() for f in self.t.features.values() if isinstance(f, NumericFeature)]
                    time.sleep(2)
                self.start_recording()
                print("Recording... Press ENTER to stop", file=sys.stderr)
                print(file=sys.stderr)
                try: input()
                except KeyboardInterrupt: pass

    def append(self, s=""):
        print(s)
        sys.stdout.flush()

    def start_recording(self):
        if self.raw: self.t.bind(on_receive_raw_data=lambda data: self.append(f"${repr(data)}"))
        else: self.t.bind(on_feature_change =
            lambda key, value, prev:
                self.append(f"${key} += {repr(value-prev)}")
                if self.relative and prev and isinstance(self.t.features[key], NumericFeature)
                else self.append(f"${key} = {repr(value)}"))
        self.t.bind(send = lambda data: self.append(f"\n# sent ${repr(data)}"))


if __name__ == '__main__': Main()

