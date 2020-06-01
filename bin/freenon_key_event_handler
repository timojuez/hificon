#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import argparse
from freenon.key_binding import send


def main():
    parser = argparse.ArgumentParser(description='Call this to handle volume button press and release events')
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument("--up", dest="button", action="store_true", help="Volume up key")
    group1.add_argument("--down", dest="button", action="store_false", help="Volume down key")
    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument("--pressed", dest="func", const="press", action="store_const", help="Key pressed")
    group2.add_argument("--released", dest="func", const="release", action="store_const", help="Key released")
    args = parser.parse_args()
    send(dict(func=args.func,button=args.button))


if __name__ == "__main__":
    main()

