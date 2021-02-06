import argparse, time
from . import Target, NAME


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f"{NAME} Debug Tool")
    parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
    parser.add_argument('-w', '--wait', metavar="sec", type=int, default=3, help='Waiting time for answer')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    t = Target(args.target, verbose=args.verbose)
    t.bind(send=lambda data: print(f"$ {data}"))
    t.bind(on_receive_raw_data=print)
    with t:
        for call in set([f.call for f in t.features.values() if f.call]):
            t.send(call)
            time.sleep(.2)
        time.sleep(args.wait)

