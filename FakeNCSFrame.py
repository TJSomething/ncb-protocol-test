from Tkinter import *
from ttk import *
from PIL import Image, ImageTk
from twisted.internet import reactor

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

