#from code import InteractiveConsole #TODO
import argparse, os, sys, time, re, ast, traceback
from threading import Thread
from contextlib import suppress
from .. import Amp, VERSION


class CLI:
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Network Amp - CLI')
        parser.add_argument('--host', type=str, default=None, help='Amp IP or hostname')
        parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--return', dest="ret", type=str, metavar="CMD", default=None, help='Return line that starts with CMD')
        group.add_argument('-f','--follow', default=False, action="store_true", help='Monitor amp messages')
        group.add_argument("file", metavar="HIFI FILE", type=str, nargs="?", help='Run hifi script')
        
        parser.add_argument("-c", "--command", default=[], metavar="CMD", nargs="+", help='Execute commands')
        parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
        self.args = parser.parse_args()
        assert(not (self.args.ret and self.args.follow))
        assert(self.args.command or not self.args.ret)
        
    def __call__(self):
        matches = (lambda cmd:cmd.startswith(self.args.ret)) if self.args.ret else None
        if len(self.args.command) == 0 and not self.args.file: self.print_header()
        self.amp = Amp(
            self.args.host, protocol=self.args.protocol, verbose=self.args.verbose)
        if self.args.follow: self.amp.bind(on_receive_raw_data=self.receive)
        with self.amp:
            self.compiler = Compiler(amp=self.amp, help=self.print_help, __matches__=matches)
            for cmd in self.args.command: self.compiler.run(cmd)
            if self.args.file: self.parse_file()
            if not self.args.file and not self.args.command: self.prompt()
    
    def print_header(self):
        print("$_ HIFI SHELL %s"%VERSION)
        print("Copyright (c) 2020 Timo L. Richter\n")

    def prompt(self):
        self.amp.bind(on_disconnected=self.on_disconnected)
        while True:
            try: cmd = input("%s $ "%self.amp.prompt).strip()
            except KeyboardInterrupt: pass
            except EOFError: break
            else: 
                try: self.compiler.run(cmd)
                except Exception as e: print(traceback.format_exc())
            print()

    def parse_file(self):
        with open(self.args.file) as fp:
            self.compiler.run(fp.read(),self.args.file,"exec")
            
    def print_help(self):
        attrs = map(lambda e: "$%s"%e,filter(lambda e:e,(self.amp.features.keys())))
        features = "".join(map(lambda e:"\t\t%s\n"%e,attrs))
        print(
            "Low level functions (protocol dependent):\n"
            "\tCMD or $'CMD'\tSend CMD to the amp\n"
            "\n"
            "High level functions:\n"
            "\t$attribute\tPrint attribute from amp\n"
            "\t$attribute=value\tSet attribute\n"
            "\tCurrent protocol supports attributes:\n%(features)s\n"
            "\n"
            "Internal functions:\n"
            "\thelp()\tShow help\n"
            "\twait(seconds)\tSleep given amount of seconds\n"
            "\texit()\tQuit\n"
            %dict(features=features)
        )

    def receive(self, data): print(data)
    
    def on_disconnected(self):
        print("\nConnection closed", file=sys.stderr)
        exit()


class AmpCommandTransformation(ast.NodeTransformer):
    """ transformer for the parsed python syntax tree """

    def visit_Expr(self, node):
        return self.make_amp_cmd(node, node.value)
        
    def make_amp_cmd(self, node, value):
        """
        handle amp commands outside of $, like MVUP;MVUP;
        """
        if isinstance(value, ast.Name): value=value.id
        
        #transforms amp functions to amp.query(...)
        #e.g. "if True: 'MVMAX 23'" -> "if True: amp.send('MVMAX 23')"
        #elif isinstance(value, Str): value = value.s
        #elif isinstance(value, Constant): value = value.value
        else: return node

        amp_ = ast.Name(id="amp", ctx=ast.Load())
        return ast.Expr(value=ast.Call(
                func=ast.Attribute(value=amp_,attr="query",ctx=ast.Load()),
                args=[ast.Str(Preprocessor.decode(value),ctx=ast.Load()),
                    ast.Name(id="__matches__",ctx=ast.Load())],
                keywords=[],
                ctx=ast.Load()),
            ctx=ast.Load())

    def visit_Name(self, node):
        """ undo preprocessing in var names """
        node.id = Preprocessor.decode(node.id)
        return node


class Regex:
    """ Regex builder for sourcecode replacements """
    
    _count = 0
    
    @classmethod
    def escapedChar(self): 
        """ matches a character and ignore backslash escaping """
        try: return r"(?:(?=(?P<backsl%(c)d>\\?))(?P=backsl%(c)d).)"%dict(c=self._count)
        finally: self._count += 1

    @classmethod
    def string(self): 
        """ matches a quoted string """
        try: return r"(?P<quote%(c)d>[\"'])%(char)s*?(?P=quote%(c)d)"%dict(
            c=self._count,char=self.escapedChar())
        finally: self._count += 1
    
    @classmethod
    def any(self, exclude=[]):
        """ like dot but includes strings in sourcecode and exclude @exclude """
        excl = "".join(list(map(lambda e: "%s|"%e, exclude)))
        return r"(?:((?!%s\"|').)?(%s)?)*"%(excl,Regex.string())

    @classmethod
    def replaceCode(self, pattern, repl, string, exclude=[], flags=re.S|re.I):
        """ replace only outside of strings """
        before = self.any(exclude=exclude)
        after = self.any(exclude=exclude)
        pattern = r"(?P<before>%s)%s(?P<after>%s)"%(before,pattern,after)
        return re.sub(
            pattern,
            r"\g<before>%s\g<after>"%repl,
            string, flags=flags)


class Preprocessor:
    """ Taking care of syntax that might be incompatible with the python parser
    like $ or ? outside of strings """
    
    replace = {"?":"PREPRO__question__"}
    
    @classmethod
    def process(self, source):
        source = "%s\n\n#$cmd; $''; cmd?\n"%source #FIXME: workaround for regex
        # handle $"cmd"
        source = Regex.replaceCode(
            r"\$(?P<cmd>%s)"%Regex.string(),
            r"amp.query(\g<cmd>)",
            source, 
            exclude=[r"\$\"",r"\$'"])
        
        # handle $var
        source = Regex.replaceCode(r"\$","amp.",source,exclude=[r"\$"])

        return self.encode(source)

    @classmethod
    def encode(self, source):
        for k,v in self.replace.items(): source = Regex.replaceCode(
            re.escape(k), re.escape(v), source, exclude=[re.escape(k)])
        return source

    @classmethod
    def decode(self, name):
        for k,v in self.replace.items(): name = name.replace(v,k)
        return name


class Compiler(Preprocessor):

    def __init__(self, **env): 
        self.env = dict(**env, wait=time.sleep, __name__="__main__")

    def run(self, source, filename="<input>", mode="single"):
        tree = ast.parse(Preprocessor.process(source),mode=mode)
        tree = ast.fix_missing_locations(AmpCommandTransformation().visit(tree))
        exec(compile(tree, filename=filename, mode=mode), self.env)
    
    
main = lambda:CLI()()
if __name__ == "__main__":
    main()

