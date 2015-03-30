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

from autobahn.twisted.websocket import WebSocketServerFactory

from autobahn.twisted.resource import WebSocketResource, \
    HTTPChannelHixie76Aware

import json
import hashlib
import random
import time

from protocol import NCSServerProtocol

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
