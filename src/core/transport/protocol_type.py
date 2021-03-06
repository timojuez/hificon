import re


class ProtocolType:

    @classmethod
    def get_title(cls): return cls.title or re.sub(r'(?<!^)(?=[A-Z])', ' ', cls.__name__)

    @classmethod
    def get_protocol(cls): return cls.protocol or re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()

    title = None
    description = None
    protocol = None
    uri_server = None
    uri_client = None

