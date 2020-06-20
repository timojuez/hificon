import sys, time, socket
from threading import Lock, Thread, Timer
from telnetlib import Telnet
from .util.system_events import SystemEvents
from .util import call_sequence, log_call
from .config import config
from .config import FILE as CONFFILE
from .amp_features import Feature, make_feature
from . import NAME


class AbstractAmp(object):
    """
    Abstract Amplifier Interface
    Note: Event callbacks (on_connect, on_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    
    protocol = "Undefined"
    host = "Undefined"
    name = None
    features = {}
    connected = False

    def __init__(self, host=None, name=None, verbose=0, **callbacks):
        super().__init__()
        self.verbose = verbose
        self.bind(**callbacks)
        self.host = host or config["Amp"].get("Host")
        self.name = name or self.name or config["Amp"].get("Name") or self.host
        if not self.host: raise RuntimeError("Host is not set! Install autosetup or set AVR "
            "IP or hostname in %s."%CONFFILE)
        
    def __enter__(self):
        self.connect()
        Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True).start()
        return self

    def __exit__(self, type, value, tb): self.disconnect()

    def bind(self, **callbacks):
        """
        bind(event=function)
        Register callback on @event. Event can be any function in Amp
        """
        for name, callback in callbacks.items():
            setattr(self, name, call_sequence(getattr(self,name), callback))

    def poweron(self, force=False):
        try:
            if not force and not config.getboolean("Amp","control_power_on") or self.power:
                return
            if config["Amp"].get("source"): self.source = config["Amp"]["source"]
            self.power = True
        except ConnectionError: pass

    def poweroff(self, force=False):
        try:
            if not force and (not config.getboolean("Amp","control_power_off") 
                or config["Amp"].get("source") and self.source != config["Amp"]["source"]): return
            self.power = False
        except ConnectionError: pass

    def connect(self, tries=1): self.connected = True

    def connect_async(self):
        Thread(target=self.connect, args=(-1,), name="connecting", daemon=True).start()
        
    def disconnect(self): self.connected = False
        
    @log_call
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        if self.verbose > 0: print("[%s] connected to %s"%(self.__class__.__name__,self.host), file=sys.stderr)
        
    @log_call
    def on_disconnected(self): self.connect_async()

    @log_call
    def on_change(self, attrib, new_val): pass
    @log_call
    def on_poweron(self): pass
    @log_call
    def on_poweroff(self): pass

    def mainloop(self): raise NotImplementedError()
    

class TelnetAmp(AbstractAmp):
    """
    This class connects to the amp via LAN and executes commands
    @host is the amp's hostname or IP.
    """

    def __init__(self, *args, **xargs):
        self.connecting_lock = Lock()
        super().__init__(*args, **xargs)

    def send(self, cmd):
        if self.verbose > 3: print("%s@%s:%s $ %s"%(NAME,self.host,self.protocol,cmd), file=sys.stderr)
        try:
            assert(self.connected)
            self._telnet.write(("%s\n"%cmd).encode("ascii"))
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
        
    def read(self, timeout=None):
        try:
            assert(self.connected)
            return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
    
    def query(self, cmd, matches=None):
        """
        send @cmd to amp and return line where matches(line) is True
        """
        if not matches: return self.send(cmd)
        else: return make_feature(self,cmd,matches).get()
    
    __call__ = query
    
    def connect(self, tries=1):
        """
        @tries int: -1 for infinite
        """
        self.connecting_lock.acquire() #blocking=False
        try:
            if self.connected: return
            while tries:
                if tries > 0: tries -= 1
                try: self._telnet = Telnet(self.host,23,timeout=2)
                except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
                    if tries == 0: raise
                else:
                    super().connect()
                    return Thread(name="on_connect",target=self.on_connect).start()
                time.sleep(3)
        finally: self.connecting_lock.release()

    def disconnect(self):
        super().disconnect()
        try: self._telnet.close()
        except AttributeError: pass

    def on_receive_raw_data(self, data): pass
    
    def mainloop(self, blocking=True):
        if not blocking: return self.__enter__()
        while True:
            try: cmd = self.read(5)
            except ConnectionError: self.connect(-1)
            else:
                # receiving
                if  not cmd: continue
                self.on_receive_raw_data(cmd) # TODO: instead use minimalistic protocol.raw_telnet and listen on on_change(None, cmd)
                if self.verbose > 3: print(cmd, file=sys.stderr)
                consumed = {attrib:f.consume(cmd) for attrib,f in self.features.items() if f.matches(cmd)}
                if not consumed: Thread(name="on_change",target=self.on_change,args=(None, cmd)).start()
                elif False in consumed.values(): continue
                for attrib,(old,new) in consumed.items():
                    if old != new: Thread(name="on_change",target=self.on_change,args=(attrib,new)).start()


BasicAmp = TelnetAmp


class CommonAmpWithEvents(SystemEvents,TelnetAmp):
    """ Amp with system events listener """
    
    @log_call
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        pass
        
    @log_call
    def on_suspend(self): pass
    
    @log_call
    def on_resume(self):
        """ Is being executed after resume computer from suspension """
        pass
        
    @log_call
    def on_start_playing(self):
        if hasattr(self,"_timer_poweroff"): self._timer_poweroff.cancel()

    @log_call
    def on_stop_playing(self):
        try: timeout = config.getfloat("Amp","poweroff_timeout")*60
        except ValueError: return
        if not timeout: return
        self._timer_poweroff = Timer(timeout,self.on_sound_idle)
        self._timer_poweroff.start()
    
    @log_call
    def on_sound_idle(self): pass
    

class AmpWithEvents(CommonAmpWithEvents):
    # TODO: move to other module?
    """ Amp implementing actions """
    
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        super().on_shutdown(sig,frame)
        try: self.poweroff()
        except ConnectionError: pass
        self.disconnect()
        
    def on_suspend(self):
        super().on_suspend()
        try: self.poweroff()
        except ConnectionError: pass
        self.disconnect()
    
    def on_resume(self):
        super().on_resume()
        self.on_disconnected()

    def on_start_playing(self):
        super().on_start_playing()
        try: self.poweron()
        except ConnectionError: pass

    def on_sound_idle(self):
        super().on_sound_idle()
        try: self.poweroff()
        except ConnectionError: pass
    

def _make_amp_mixin(**features):
    """
    Make a class where all attributes are getters and setters for amp properties
    args: class_attribute_name=MyFeature
        where MyFeature inherits from Feature
    """
    
    class FeatureMixin(object):
        """ apply @features to Amp """

        def __init__(self,*args,**xargs):
            self.features = {}
            for k,v in features.items(): v(self,k)
            super().__init__(*args,**xargs)
        
        def on_connect(self):
            for f in self.features.values(): f.unset()
            super().on_connect()
        
        def _set_feature_value(self, name, value):
            self.features[name].set(value)
        

    class SendOnceMixin(object):
        """ prevent the same values from being sent to the amp in a row """

        def __init__(self,*args,**xargs):
            self._block_on_set = {}
            super().__init__(*args,**xargs)
            
        def _set_feature_value(self, name, value):
            if name in self._block_on_set and self._block_on_set[name] == value:
                return
            self._block_on_set[name] = value
            super()._set_feature_value(name,value)
            
        def on_change(self,*args,**xargs):
            self._block_on_set.clear() # unblock values after amp switches on
            super().on_change(*args,**xargs)
        
        
    dict_ = dict()
    try: dict_["protocol"] = sys._getframe(3).f_globals['__name__']
    except: pass
    dict_.update({
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self._set_feature_value(k,val)
        )
        for k,v in features.items()
    })
    cls = type("AmpFeatures", (SendOnceMixin,FeatureMixin), dict_)
    return cls


def _make_amp(features, base_cls=object):
    for name in features.keys(): 
        if hasattr(base_cls,name):
            raise KeyError("Key `%s` is ambiguous and may not be used as a feature."%name)
    return type("Amp", (_make_amp_mixin(**features),base_cls), dict())
    

def make_basic_amp(**features): return _make_amp(features, BasicAmp)
def make_amp(**features): return _make_amp(features, AmpWithEvents)

