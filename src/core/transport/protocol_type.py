import re


class ProtocolType:
    title = None
    description = None
    Client = None
    Server = None
    client_args_help = None # tuple, if None, will be read from Client.init_args_help
    server_args_help = None # tuple

    @classmethod
    def get_title(cls): return cls.title or re.sub(r'(?<!^)(?=[A-Z])', ' ', cls.__name__)

    @classmethod
    def get_client_uri(cls):
        args = cls.client_args_help
        if args is None: args = getattr(cls.Client,"init_args_help",None)
        if args is not None: return ":".join((cls.protocol, *args))

    @classmethod
    def get_server_uri(cls):
        args = cls.server_args_help
        if args is None: args = getattr(cls.Server,"init_args_help",None)
        if args is not None: return ":".join((cls.protocol, *args))

