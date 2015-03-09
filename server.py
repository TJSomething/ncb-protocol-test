###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

import sys

from twisted.internet import reactor
from twisted.internet import task
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol

from autobahn.twisted.resource import WebSocketResource, \
    HTTPChannelHixie76Aware

import json
import hashlib
import random

subscribers = []
def sendData():
    data = [random.random() for i in xrange(3)]
    print "Sending data: %s" % data
    for sub in subscribers:
        sub.sendMessage(str(data))

class NCSServerProtocol(WebSocketServerProtocol):
    messages = []
    messagesLeft = None
    path = None

    def handleSensors(self, sensors):
        self.messages = [sensors]
        self.messagesLeft = len(self.messages[0]["arrays"])

    def handleData(self, data):
        self.messages.append(data)
        self.messagesLeft -= 1

        if self.messagesLeft == 0:
            self.messagesLeft = None
            self.handleMessages()

    def handleMessages(self):
        def setNested(l, path, value):
            splitPath = path.split(".")
            for key in splitPath[:-1]:
                if isinstance(l, list):
                    l = l[int(key)]
                else:
                    l = l[key]

            if isinstance(l, list):
                l[int(splitPath[-1])] = value
            else:
                l[splitPath[-1]] = value

        sensors = self.messages[0]

        # Typically, we'd want to put the binary into the sensors structure and
        # then process that.
        # But, since this is just an example, we're going to replace the locations
        # where the data would go with a string describing the data and print
        # it.
        for index, message in enumerate(self.messages[1:]):
            path = sensors["arrays"][index]["path"]
            dataDescriptor = "%s[%d]" % (sensors["arrays"][index]["type"], len(message))
            setNested(sensors, path, dataDescriptor)

        print sensors

    def onConnect(self, request):
        self.path = request.path
        subscribers.append(self)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.handleSensors(json.loads(payload))
        else:
            self.handleData(payload)

    def onClose(self, wasClean, code, reason):
        subscribers.remove(self)

if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        log.startLogging(sys.stdout)
        debug = True
    else:
        debug = False

    factory = WebSocketServerFactory("ws://localhost:8080",
                                     debug=debug,
                                     debugCodePaths=debug)

    factory.protocol = NCSServerProtocol
    factory.setProtocolOptions(allowHixie76=True)  # needed if Hixie76 is to be supported

    resource = WebSocketResource(factory)

    # we server static files under "/" ..
    root = File(".")

    # and our WebSocket server under "/ws"
    root.putChild("ws", resource)

    # both under one Twisted Web Site
    site = Site(root)
    site.protocol = HTTPChannelHixie76Aware  # needed if Hixie76 is to be supported
    reactor.listenTCP(8080, site)
    print "Server running on localhost:8080..."

    l = task.LoopingCall(sendData)
    l.start(1.0)

    reactor.run()
