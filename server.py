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
from twisted.internet import tksupport
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
from Tkinter import *
from ttk import *

class FakeNCSFrame(Frame):
    def createWidgets(self):
        self.data_view = Listbox(self)
        self.data_view.pack(fill=BOTH, expand=1)

        self.output_sliders = []
        for i in xrange(self.outputs):
            s = Scale(self, from_=-100, to=100, orient=HORIZONTAL)
            s.pack(fill=X)
            self.output_sliders.append(s)

        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["command"] = self.quit
        self.QUIT.pack(side="bottom")

    def updateView(self, data):
        def addKey(key, value, depth=0):
            indent = '  ' * depth
            if type(value) == list:
                self.data_view.insert('end', '%s%s:' % (indent, str(key)))
                for index, item in enumerate(value):
                    addKey(index, item, depth+1)
            elif type(value) == dict:
                self.data_view.insert('end', '%s%s:' % (indent, str(key)))
                for index, item in value.iteritems():
                    addKey(index, item, depth+1)
            else:
                self.data_view.insert('end', '%s%s: %s' % (indent, str(key), str(value)))

        self.data_view.delete(0, END)
        for k,v in data.iteritems():
            addKey(k,v)

    def quit(self):
        self.master.destroy()
        reactor.stop()

    def __init__(self, master=None, outputs=0):
        Frame.__init__(self, master)

        self.outputs = outputs

        self.pack()
        self.createWidgets()


class FakeNCS(object):
    frequency = 100

    def __init__(self, outputs):
        self.root = Tk()
        self.app = FakeNCSFrame(master=self.root, outputs=outputs)
        self.app.pack(fill=BOTH, expand=YES)
        self.root.protocol("WM_DELETE_WINDOW", self.app.quit)
        tksupport.install(self.root)

        self.subscribers = []
        self.send_loop = task.LoopingCall(self.send)
        self.send_loop.start(1.0/FakeNCS.frequency)

    def receive(self, data):
        self.app.updateView(data)

    def send(self):
        outputs = [s.get() for s in self.app.output_sliders]
        for sub in self.subscribers:
            sub(outputs)

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def unsubscribe(self, callback):
        self.subscribers.remove(callback)

instance = FakeNCS(3)
def getNCS(id):
    """This could make an object to interface with NCS, but we're
    going to use something static for now."""
    return instance

class NCSServerProtocol(WebSocketServerProtocol):
    messages = []
    messagesLeft = None
    path = None

    def sendReports(self, reports):
        self.sendMessage(str(reports))

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

        self.ncs.receive(sensors)


    def onConnect(self, request):
        self.path = request.path
        self.ncs = getNCS(0)
        self.ncs.subscribe(self.sendReports)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.handleSensors(json.loads(payload))
        else:
            self.handleData(payload)

    def onClose(self, wasClean, code, reason):
        self.ncs.unsubscribe(self.sendReports)

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

    reactor.run()
