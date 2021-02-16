import argparse, time, sys, os
from . import Target


class Main:
    
    def __init__(self):
        script = os.path.basename(__file__)
        parser = argparse.ArgumentParser(description=f'Tool for creating a HiFi script for HiFiSh. It can record target changes to repeat the actions later by calling the HiFi script. Writes to stdout. Example: {script} > batch.hifi && hifish batch.hifi')
        parser.add_argument('-a', '--all', action="store_true", help='Include all current feature values, not just recorded ones')
        parser.add_argument("-r", "--raw", action="store_true", help="Use low level commands")
        parser.add_argument("--debug", action="store_true", help="Same as -ar")
        parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
        parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
        args = parser.parse_args()
        all_features = args.all or args.debug
        raw = args.raw or args.debug
        t = Target(args.target, verbose=args.verbose)
        def append(s=""): print(s)
        append("#!/usr/bin/env hifish")
        append("#")
        append(f"# CREATED WITH {script}")
        append("#")
        append()
        if raw: t.bind(on_receive_raw_data=lambda data: append(f"${repr(data)}"))
        else: t.bind(on_feature_change=lambda key, value, *args, **xargs: append(f"${key} = {repr(value)}"))
        t.bind(send = lambda data: append(f"\n# sent ${repr(data)}"))
        with t:
            if all_features:
                for call in set([f.call for f in t.features.values() if f.call]):
                    t.send(call)
                    time.sleep(.2)
                time.sleep(3)
            else:
                print("Recording... Press ENTER to stop", file=sys.stderr)
                print(file=sys.stderr)
                input()


if __name__ == '__main__': Main()

