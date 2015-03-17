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
from PIL import Image, ImageTk
import time

class FakeNCSFrame(Frame):
    def createWidgets(self):
        padding = {"padx": 10, "pady": 10}
        self.data_frame = Frame(self, border=2, relief=SUNKEN)
        self.scroll = Scrollbar(self.data_frame)
        self.scroll.pack(side=RIGHT, fill=Y)
        self.data_view = Text(self.data_frame, border=0, yscrollcommand=self.scroll.set)
        self.data_view.config(state=DISABLED)
        self.data_view.pack(side="top", fill=BOTH, expand=1)
        self.scroll.config(command=self.data_view.yview)
        self.data_frame.pack(fill=BOTH, expand=1, **padding)

        self.output_sliders = []
        self.output_values = []
        for i in xrange(self.outputs):
            v = DoubleVar()
            self.output_values.append(v)
            s_label = Label(self, textvariable=v)
            s_label.pack(side="top")
            s = Scale(self, from_=-100, to=100, orient=HORIZONTAL, variable=v)
            s.pack(fill=X, side="top", **padding)
            self.output_sliders.append(s)

        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["command"] = self.quit
        self.QUIT.pack(side="bottom", **padding)

    def updateView(self, data):
        # If we can expect that it will take too long render a frame,
        # then skip frames
        start = time.time()
        if start - self.last_render < self.max_render_time:
            return None

        self.images = []
        def addKey(key, value, depth=0):
            indent = '  ' * depth
            if type(value) == list:
                self.data_view.insert('end', '%s%s:\n' % (indent, str(key)))
                for index, item in enumerate(value):
                    addKey(index, item, depth+1)
            elif type(value) == dict:
                if "image" in value and "width" in value and "height" in value:
                    image = Image.frombytes("RGBA",
                        (value["width"], value["height"]), value["image"])
                    self.images.append(ImageTk.PhotoImage(image))
                    self.data_view.insert('end', '%s%s:\n%s  ' % (indent, str(key), indent))
                    self.data_view.image_create('end', image=self.images[-1])
                    self.data_view.insert('end', '\n')
                else:
                    self.data_view.insert('end', '%s%s:\n' % (indent, str(key)))
                    for index, item in value.iteritems():
                        addKey(index, item, depth+1)
            else:
                self.data_view.insert('end', '%s%s: %s\n' % (indent, str(key), str(value)))

        old_top = self.data_view.yview()
        self.data_view.config(state=NORMAL)
        self.data_view.delete(1.0, END)
        for k,v in data.iteritems():
            addKey(k,v)
        self.data_view.config(state=DISABLED)
        new_top = self.data_view.yview()
        # Find the ratio of the heights before and after redrawing and convert the old top
        # into the new coordinate system
        self.data_view.yview_moveto((new_top[1]-new_top[0])/(old_top[1]-old_top[0]) * old_top[0])

        if time.time() - start > self.max_render_time:
            self.max_render_time = time.time() - start


    def quit(self):
        self.master.destroy()
        reactor.stop()

    def __init__(self, master=None, outputs=0):
        Frame.__init__(self, master)

        self.outputs = outputs
        self.max_render_time = 0.0
        self.last_render = 0.0

        self.pack()
        self.createWidgets()


class FakeNCS(object):
    frequency = 100

    def __init__(self, outputs):
        self.root = Tk()
        self.root.title("NCVB Server Demo")
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
        outputs = [s.get() for s in self.app.output_values]
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
        self.messagesLeft = json.loads(sensors)["messages"]

    def handleData(self, data):
        self.messages.append(data)
        self.messagesLeft -= 1

        if self.messagesLeft == 0:
            self.messagesLeft = None
            self.handleMessages()

    def handleMessages(self):
        def deserializeArrays(obj):
            if "index" in obj and "type" in obj:
                return self.messages[obj["index"]+1]
            else:
                return obj
            
        sensors = json.loads(self.messages[0], object_hook=deserializeArrays)["sensors"]

        self.ncs.receive(sensors)

    def onConnect(self, request):
        self.path = request.path
        self.ncs = getNCS(0)
        self.ncs.subscribe(self.sendReports)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.handleSensors(payload)
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
