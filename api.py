#-*- coding: UTF-8 -*-
from dpa.client.XMLRPCProxy import XMLRPCProxy

def api():
  return XMLRPCProxy('127.0.0.1:13888', path='/client')

if __name__ == "__main__":
  print api().connCheck()
