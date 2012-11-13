import sys, os, time
from gevent_zeromq import zmq
import monitor

ctx = zmq.Context()
sub_addr, router_addr = sys.argv[1:]
sub_sock = ctx.socket(zmq.SUB)
sub_sock.setsockopt(zmq.SUBSCRIBE, '')
sub_sock.connect(sub_addr)
req_sock = ctx.socket(zmq.REQ)
req_sock.connect(router_addr)

class Plugin(object):
    last_heartbeat = 0
    def _send(self, msg):
        req_sock.send_json(msg)
        return req_sock.recv_json()

    def __init__(self):
        self.handlers = []
        self.raw_handlers = []
        self.tickers = []
        self.monitor = monitor.Monitor()

    def addHandler(self, exp, handler):
        self.handlers.append((exp, handler))

    def addRawHandler(self, exp, handler):
        self.raw_handlers.append((exp, handler))

    def addTicker(self, ticker):
        self.tickers.append(ticker)

    def run(self):
        last_monitor_check = 0
        last_ticker = 0
        while True:
            now = time.time()
            if now - last_monitor_check > 5:
                if self.monitor.check_ages():
                    sys.exit(0)
                last_monitor_check = now

            if now - self.last_heartbeat > 10:
                self._send({"action": "heartbeat", "pid": os.getpid()})
                self.last_heartbeat = now

            # Call tickers
            if now - last_ticker > 10:
                for t in self.tickers:
                    t(self)
                last_ticker = now

            if 0 == sub_sock.poll(10000):
                continue

            msg = sub_sock.recv_json()

            if 'privmsg' in msg:
                for exp, handler in self.handlers:
                    text = msg['privmsg']['text']
                    m = exp.match(text)
                    if m:
                        handler(self, msg, m)

            for exp, handler in self.raw_handlers:
                    m = exp.match(msg['data'])
                    if m:
                        handler(self, msg, m)

    def call(self, method, args=None, kwargs=None):
        msg = {"action": "call", "method": method}
        if args is not None:
            msg['args'] = args
        if kwargs is not None:
            msg['kwargs'] = kwargs
        return self._send(msg)

    def log(self, msg):
        return self.call("log", args=(msg,))

    def send(self, msg):
        return self.call("send", kwargs={"data": msg})

    def reply(self, msg, channel=None, nick=None):
        return self.call("reply", kwargs={"msg": msg, "channel": channel, "nick": nick})
