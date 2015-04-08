from twisted.web import resource
from protocol import NCSServerProtocol
from FakeNCS import FakeNCS
import json

from autobahn.twisted.websocket import WebSocketServerFactory

from autobahn.twisted.resource import WebSocketResource, \
    HTTPChannelHixie76Aware

class SimulationFactory(resource.Resource):
    def __init__(self):
        factory = WebSocketServerFactory("ws://localhost:8080")

        factory.protocol = NCSServerProtocol
        factory.setProtocolOptions(allowHixie76=True)  # needed if Hixie76 is to be supported

        self.ws_resource = WebSocketResource(factory)

        self.children = {}

    def create(self, params):
        """Creates a "simulation" with the given parameters and returns
        the instance number."""

        NCSServerProtocol.instances.append(FakeNCS(params))
        index = len(NCSServerProtocol.instances) - 1
        self.putChild(str(index), self.ws_resource)

        return len(NCSServerProtocol.instances) - 1

    def getChild(self, name, request):
        if name == "":
            return self
        return resource.Resource.getChild(self, name, request)

    def render_POST(self, request):
        path = "/".join(request.prepath)
        raw_params = request.content.read()
        index = self.create(raw_params)
        host = request.requestHeaders.getRawHeaders("host")[0]
        request.setHeader('Access-Control-Allow-Origin', '*')
        return "ws://%s/%s%d" % (host, path, index)
