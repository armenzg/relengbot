#!/usr/bin/python
import sys
import eventlet
import shlex
import os
import traceback
import subprocess

ircbot = eventlet.import_patched('ircbot')
irclib = eventlet.import_patched('irclib')

from irclib import irc_lower, ServerConnectionError, ip_quad_to_numstr, ip_numstr_to_quad, nm_to_n, is_channel

import commands

import logging
log = logging.getLogger(__name__)

class SSLIrcBot(ircbot.SingleServerIRCBot):
    def _connect(self):
        """[Internal]"""
        password = None
        ssl = False
        if len(self.server_list[0]) > 2:
            ssl = self.server_list[0][2]
        if len(self.server_list[0]) > 3:
            password = self.server_list[0][3]
        try:
            self.connect(self.server_list[0][0],
                         self.server_list[0][1],
                         self._nickname,
                         password,
                         ircname=self._realname,
                         ssl=ssl)
        except ServerConnectionError:
            pass

class RelengBot(SSLIrcBot):
    def __init__(self, start_channels, logchannel, nickname, server, port=6667, ssl=False):
        SSLIrcBot.__init__(self, [(server, port, ssl)], nickname, nickname)
        self.start_channels = start_channels
        self.logchannel = logchannel
        self.commands = {
                'disconnect': commands.Disconnect(self),
                'die': commands.Die(self),
                'ping': commands.Ping(self),
                'reboot': commands.Reboot(self),
                'join': commands.Join(self),
                'leave': commands.Leave(self),
                'dance': commands.Dance(self),
            }
        self.watchers = [
                commands.BugWatcher(self),
                commands.HungSlaveWatcher(self),
                ]

        self.periodic_commands = [
                (commands.HungSlaveChecker(self), 3600),
                ]

        self._file_ages = {}
        self._monitor_files()

    def _monitor_files(self):
        log.info("checking files")
        import sys
        for module in sys.modules.values():
            if not hasattr(module, '__file__'):
                continue

            # Get the age of the file
            filename = module.__file__
            mtime = os.path.getmtime(filename)

            if filename.endswith(".pyc"):
                # Check the .py file too
                sourcefile = filename[:-4] + ".py"
                if os.path.exists(sourcefile):
                    mtime = os.path.getmtime(sourcefile)
                    filename = sourcefile

            old_mtime = self._file_ages.get(filename)
            if old_mtime and mtime > old_mtime:
                # Something has changed, restart!
                self.do_restart("self-update")
                return

            self._file_ages[filename] = mtime

        # Try again later
        eventlet.spawn_after(10, self._monitor_files)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        for channel in self.start_channels:
            log.info("Joining %s", channel)
            c.join(channel)

        # Start up periodic commads
        def command_loop(command, interval):
            try:
                command.run()
            except:
                traceback.print_exc()
                msg = "Unhandled exception: %s" % traceback.format_exc()
                self.log(msg)
            self.log("Scheduling %s to run in %i seconds" % (command, interval))
            eventlet.spawn_after(interval, command_loop, command, interval)

        for command, interval in self.periodic_commands:
            try:
                eventlet.spawn(command_loop, command, interval)
            except:
                traceback.print_exc()

    def log(self, msg):
        self._sendlines(self.connection, self.logchannel, msg)

    def scan_msg(self, c, e):
        s = e.arguments()[0]
        for w in self.watchers:
            try:
                w.send_input(c, e)
            except:
                traceback.print_exc()
                msg = "Unhandled exception: %s" % traceback.format_exc()
                self.log(msg)

    def sendlines(self, c, e, m):
        target = e.target()
        if not is_channel(target):
            target = nm_to_n(e.source())
        self._sendlines(c, target, m)

    def _sendlines(self, c, target, m):
        for line in m.split("\n"):
            c.privmsg(target, line)

    def on_privmsg(self, c, e):
        self.scan_msg(c, e)
        self.do_command(e, e.arguments()[0])

    def on_pubmsg(self, c, e):
        self.scan_msg(c, e)
        a = e.arguments()[0].split(":", 1)
        if len(a) > 1 and irc_lower(a[0]) == irc_lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def do_command(self, e, cmd):
        try:
            c = self.connection

            args = shlex.split(cmd)
            cmd = args[0]

            if cmd in self.commands:
                self.log("executing %s" % cmd)
                self.commands[cmd].run(c, e, args)
            elif cmd == "restart":
                self.log("restarting")
                self.do_restart()
            elif cmd == 'help':
                self.sendlines(c, e, "Known commands: %s" % ", ".join(self.commands.keys()))

        except SystemExit:
            raise
        except:
            traceback.print_exc()
            msg = "Unhandled exception: %s" % traceback.format_exc()
            self.sendlines(c, e, msg)

    def do_restart(self, message=None):
        if message:
            message = "Restarting! %s" % message
        else:
            message = "Restarting!"
        print message
        self.disconnect(message)
        cmd = [sys.executable] + sys.argv
        print "Starting new process", cmd
        subprocess.Popen(cmd)
        print "Exiting"
        sys.exit(0)

if __name__ == '__main__':
    b = RelengBot(['#relengbot'], '#relengbot', 'relengbot', '63.245.208.159', 6697, ssl=True)
    b.start()
    print "So long..."
