from flask import Flask
from dpa.client.XMLRPCProxy import XMLRPCProxy
import json
from datetime import datetime as datetime

def api():
  h = '%s:%s' % ('192.168.224.205', str(12347))
  testSrv = XMLRPCProxy(h, path='/client', )
  return testSrv

app = Flask(__name__)
server = api()

@app.route('/api/connCheck')
def connCheck():
    return json.dumps({'status': server.connCheck()})

@app.route('/api/getScalesLocal')
def getScales():
    return json.dumps(server.getScalesLocal(), indent=4, sort_keys=True, default=str)

@app.route('/api/createScale/<name>/<ip>')
def createScale(name, ip):
    return server.createScaleLocal(name, ip)


if __name__ == '__main__':
    app.run()
