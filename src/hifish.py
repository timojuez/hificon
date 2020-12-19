import argparse, os, sys, time, re, ast, traceback
from code import InteractiveConsole
from threading import Thread
from contextlib import suppress
from decimal import Decimal
from . import Amp, amp, VERSION, AUTHOR
try: import readline
except ImportError: pass


class CLI:
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Network Amp - CLI')
        parser.add_argument('--host', type=str, default=None, help='Amp IP or hostname')
        parser.add_argument('--port', type=int, default=None, help='Amp port')
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
            host=self.args.host, port=self.args.port, protocol=self.args.protocol, verbose=self.args.verbose)
        if self.args.follow: self.amp.bind(on_receive_raw_data=self.receive)
        with self.amp:
            self.compiler = Compiler(
                # environment variables for hifish
                __query__ = self.query,
                __return__ = matches,
                __wait__ = .1,
                Decimal = Decimal,
                amp = self.amp,
                help = self.print_help,
                help_attr = self.print_help_attr,
            )
            for cmd in self.args.command: self.compiler.run(cmd)
            if self.args.file: self.parse_file()
            if not self.args.file and not self.args.command or self.args.follow: self.prompt()
    
    def query(self, cmd, matches, wait):
        """ calling $"cmd" or $'cmd' from within hifish. @matches comes from --return """
        r = self.amp.query(cmd, matches)
        if wait: time.sleep(wait)
        return r
        
    def print_header(self):
        print("$_ HIFI SHELL %s"%VERSION)
        print("Copyright (c) 2020 %s\n"%AUTHOR)
        print("To get started, write help()\n")

    def prompt(self):
        self.amp.bind(on_disconnected=self.on_disconnected)
        ic = InteractiveHifish(
            prompt="%s $ "%self.amp.prompt, compiler=self.compiler, locals=self.compiler.env)
        ic.interact(banner="", exitmsg="")

    def parse_file(self):
        with open(self.args.file) as fp:
            self.compiler.run(fp.read(),self.args.file,"exec")
            
    def print_help(self):
        print(
            "Internal functions:\n"
            "\thelp()\tShow help\n"
            "\twait(seconds)\tSleep given amount of seconds\n"
            "\texit()\tQuit\n"
            "\n"
            "High level functions (protocol independent)\n"
            "\t$attribute\tVariable that contains amp's attribute, potentially read and writeable\n"
            "\tTo see a list of attributes, type help_attr()\n"
            "\n"
            "Low level functions (protocol dependent)\n"
            "\tCMD or $'CMD'\tSend CMD to the amp and return answer\n"
        )

    def print_help_attr(self):
        print("Current protocol supports these attributes:\n")
        features = filter(lambda e:e[0], self.amp.features.items())
        for name, f in sorted(features, key=lambda e:e[0]):
            print("\t$%(name)s  %(title)s  %(type)s "%dict(name=name, type=f.type.__name__, title=f.name), end="")
            if isinstance(f,amp.features.IntFeature) or isinstance(f,amp.features.DecimalFeature):
                print("[%s..%s] "%(f.min,f.max), end="")
            elif isinstance(f,amp.features.SelectFeature) or isinstance(f,amp.features.BoolFeature): 
                print(f.options, end="")
            print()
        print()
    
    def receive(self, data): print(data)
    
    def on_disconnected(self):
        print("\nConnection closed", file=sys.stderr)
        exit()


class AmpCommandTransformation(ast.NodeTransformer):
    """ transformer for the parsed python syntax tree """
    
    def __init__(self, preprocessor):
        super().__init__()
        self.preprocessor = preprocessor
        
    def _query_call(self, cmd):
        """ returns __query__(@cmd, __return__, __wait__) """
        node = ast.Call(
            func=ast.Name(id="__query__", ctx=ast.Load()),
            args=[
                ast.Str(self.preprocessor.decode(cmd),ctx=ast.Load()),
                ast.Name(id="__return__",ctx=ast.Load()),
                ast.Name(id="__wait__",ctx=ast.Load()),
            ],
            keywords=[],
            ctx=ast.Load())
        self.generic_visit(node)
        return node
     
    def visit_Expr(self, node):
        """ handle amp commands outside of $, like MVUP;MVUP; """
        if isinstance(node.value, ast.Name): node.value = self._query_call(node.value.id)
        self.generic_visit(node)
        return node
        
    def _visit_Str(self, node, value):
        """ handle $'cmd' """
        for r,o in (dict(self.preprocessor.replace)["$'"], dict(self.preprocessor.replace)['$"']):
            if value.startswith(o): return self._query_call(value.replace(o,"",1))
        return node
            
    def visit_Constant(self, node): return self._visit_Str(node, node.value) if isinstance(node.value, str) else node
        
    def visit_Str(self, node): return self._visit_Str(node, node.s)
    
    def visit(self, node):
        r = super().visit(node)
        # undo preprocessing
        if isinstance(node, ast.Name): node.id = self.preprocessor.decode(node.id)
        elif isinstance(node, ast.ClassDef): node.name = self.preprocessor.decode(node.name)
        elif isinstance(node, ast.keyword): node.arg = self.preprocessor.decode(node.arg)
        elif isinstance(node, ast.AsyncFunctionDef): node.name = self.preprocessor.decode(node.name)
        elif isinstance(node, ast.FunctionDef): node.name = self.preprocessor.decode(node.name)
        elif isinstance(node, ast.arg): node.arg = self.preprocessor.decode(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str): node.value = self.preprocessor.decode(node.value)
        elif isinstance(node, ast.Str): node.s = self.preprocessor.decode(node.s)
        return r
        

class Preprocessor:
    """ Taking care of syntax that might be incompatible with the python parser
    like $ or ? outside of strings """
    
    replace = [
        #str,   replace,            ocurrance in string after parsing
        ("?",   ("__quest__",       "__quest__")),
        ("$'",  ("'__dollar1__",    "__dollar1__")),
        ('$"',  ('"__dollar2__',    "__dollar2__")),
        ("$",   ("amp.",            "amp.")),
    ]
    
    def __init__(self, source):
        self.source = source
        def find_unique(r, o):
            if o in source: return find_unique("%s1"%r, "%s1"%o)
            else: return r,o
        self.replace = [(s,find_unique(r,o)) for s,(r,o) in self.replace]
    
    def encode(self):
        source = self.source
        for s,(repl,find) in self.replace: source = source.replace(s,repl)
        return source
        
    def decode(self, data):
        for s,(repl,find) in self.replace: data = data.replace(repl,s)
        return data


class Compiler(Preprocessor):

    def __init__(self, **env): 
        self.env = dict(**env, wait=time.sleep, __name__="__main__")

    def compile(self, source, filename, mode):
        preprocessor = Preprocessor(source)
        source_p = preprocessor.encode()
        tree = ast.parse(source_p, mode=mode)
        tree = AmpCommandTransformation(preprocessor).visit(tree)
        tree = ast.fix_missing_locations(tree)
        #print(ast.dump(tree))
        return compile(tree, filename=filename, mode=mode)

    __call__ = compile
    
    def run(self, source, filename="<input>", mode="single"):
        exec(self(source, filename, mode), self.env)
        
    
class InteractiveHifish(InteractiveConsole):
    
    def __init__(self, *args, compiler=None, prompt=None, **xargs):
        super().__init__(*args,**xargs)
        if compiler: self.compile.compiler = compiler
        if prompt: sys.ps1 = prompt


main = lambda:CLI()()
if __name__ == "__main__":
    main()

