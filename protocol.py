from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.websocket.http import HttpException
from FakeNCS import FakeNCS
import json

class NCSServerProtocol(WebSocketServerProtocol):
    # A list of active "simulations"
    instances = []

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
        index = request.path.split("/")[-1]
        try:
            self.ncs = NCSServerProtocol.instances[int(index)]
        except IndexError:
            raise HttpException(404, "Simulation does not exist")

        self.ncs.subscribe(self.sendReports)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            self.handleSensors(payload)
        else:
            self.handleData(payload)

    def onClose(self, wasClean, code, reason):
        if hasattr(self, "ncs"):
            self.ncs.unsubscribe(self.sendReports)
