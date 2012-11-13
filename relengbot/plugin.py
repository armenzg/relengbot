"""
module for base plugin class, utilities, etc.
"""
from multiprocessing import Process, Pipe
import time

import monitor

class Plugin(object):
    def __init__(self):
        self.monitor = monitor.Monitor()
        self.pipe = None

    def start(self):
        self.pipe, child = Pipe()
        self.proc = Process(target=self.run, args=(child,))
        self.proc.start()

    def send(self, msg):
        self.pipe.send(msg)

    def join(self):
        self.proc.join()

    def run(self, pipe):
        while True:
            obj = pipe.recv()
            print "Got", obj
            #time.sleep(10)
            if self.monitor.check_ages():
                print "Shutting down"
                break

if __name__ == '__main__':
    p = Plugin()

    p.start()
    p.send("hello")
    time.sleep(10)
    p.send("there")
    time.sleep(10)
    p.send("world")

    p.join()
