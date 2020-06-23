import argparse, os, sys, time
from threading import Thread
from contextlib import suppress
from .. import Amp, VERSION


class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Network Amp - CLI')
        parser.add_argument('--host', type=str, default=None, help='Amp IP or hostname')
        parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--return', dest="ret", type=str, metavar="CMD", default=None, help='Return line that starts with CMD')
        group.add_argument('-f','--follow', default=False, action="store_true", help='Monitor amp messages')
        group.add_argument("file", metavar="HIFI FILE", type=str, nargs="?", help='Run hifi script')
        
        parser.add_argument("-c", "--command", default=[], metavar="CMD", nargs="*", help='Execute commands')
        parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
        self.args = parser.parse_args()
        assert(not (self.args.ret and self.args.follow))
        assert(self.args.command or not self.args.ret)
        
    def __call__(self):
        self.matches = (lambda cmd:cmd.startswith(self.args.ret)) if self.args.ret else None
        if len(self.args.command) == 0 and not self.args.file: self.print_header()
        self.amp = Amp(
            self.args.host, protocol=self.args.protocol, verbose=self.args.verbose)
        if self.args.follow: self.amp.bind(on_receive_raw_data=self.receive)
        with self.amp:
            for cmd in self.args.command: 
                p = self.parse(cmd)
                print(p)
                if p == False: sys.exit(1)
            if self.args.file: self.parse_file()
            if not self.args.file and not self.args.command: self.prompt()
    
    def print_header(self):
        print("$_ HIFI SHELL %s\n"%VERSION)

    def prompt(self):
        self.amp.bind(on_disconnected=self.on_disconnected)
        while True:
            try: cmd = input("%s $ "%self.amp.prompt).strip()
            except KeyboardInterrupt: pass
            except EOFError: break
            else: 
                try: p = self.parse(cmd)
                except Exception as e: print(repr(e))
                else:
                    if p: print(p)
            print()
        return

    def parse_file(self):
        with open(self.args.file) as fp:
            for line in fp.read(): self.parse(line.strip())
            
    def print_help(self):
        print("Commands:\n"
            "\tCMD\tSend CMD to the amp\n"
            "\t$?\tPrint all available amp attributes for current protocol\n"
            "\t$attribute\tPrint attribute from amp\n"
            "\t!help\tShow help\n"
            "\t!wait\tSleep one second\n"
            "\t!exit\tQuit\n"
        )
    
    def parse(self, cmd):
        if cmd.startswith("//") or cmd.startswith("#"): return
        elif cmd in ("?","help","!help"): return self.print_help()
        elif cmd.startswith("$"): return self.parse_attr(cmd[1:])
        elif cmd == "!wait": time.sleep(1)
        elif cmd == "!exit": exit()
        else: return self.amp.query(cmd,self.matches)

    def parse_attr(self, attr):
        if attr == "?":
            attrs = map(lambda e: "$%s"%e,filter(lambda e:e,(self.amp.features.keys())))
            return ", ".join(attrs)
        elif "=" in attr:
            attr,value = attr.split("=")
            attr = attr.strip()
            if attr not in self.amp.features: raise AttributeError("Unknown variable")
            value = guess_type(value.strip())
            setattr(self.amp,attr, value)
        else: return getattr(self.amp,attr)
    
    def receive(self, data): print(data)
    
    def on_disconnected(self):
        print("\nConnection closed", file=sys.stderr)
        exit()
        

def guess_type(val):
    def _bool(val):
        try: return {"True":True, "False": False}[val]
        except KeyError as e: raise ValueError(e)
    for t in [_bool, int, float, str]: 
        with suppress(ValueError): return t(val)
    

main = lambda:CLI()()
if __name__ == "__main__":
    main()

