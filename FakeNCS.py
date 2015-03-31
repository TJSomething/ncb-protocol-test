from Tkinter import *
from ttk import *
from twisted.internet import tksupport
from FakeNCSFrame import FakeNCSFrame
from twisted.internet import task

class FakeNCS(object):
    frequency = 100
    # This stores the original root window
    master_root = None

    def __init__(self, outputs):
        if self.master_root is None:
            self.root = FakeNCS.master_root = Tk()
        else:
            self.root = Toplevel(FakeNCS.master_root)
        self.root.title("NCVR Server Demo")
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

