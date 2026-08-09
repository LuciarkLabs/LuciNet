class ParseError(Exception):

    pass

class UnsupportedProtocolError(ParseError):

    pass

class ValidationError(ParseError):

    pass
