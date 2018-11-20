from email.Message import Message
from email.Parser import Parser


class HTTPHeaders(Message):
  pass

def parseHTTPHeaders(hfile):
  return Parser(_class=HTTPHeaders).parse(hfile, headersonly=True)
