from autobahn.twisted.websocket import WebSocketServerProtocol
from FakeNCS import FakeNCS

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
