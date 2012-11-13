#!/usr/bin/python
import paramiko
import logging
import re
import time
import urllib
log = logging.getLogger(__name__)

class WarningPolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        log.debug("Warning: unknown host key for %s", hostname)

class Slave(object):
    def __init__(self, client, hostname):
        self.client = client
        self.hostname = hostname

        self.transport = client.get_transport()
        channel = self.channel = self.transport.open_session()
        channel.get_pty()
        channel.invoke_shell()

    def graceful_shutdown(self):
        tacinfo = self.get_tacinfo()
        if tacinfo is None:
            log.error("Couldn't get info from buildbot.tac; slave is disabled?")
            return False

        host, port, slavename = tacinfo

        if 'staging' in host:
            log.warn("Ignoring staging host %s for slave %s", host, self.hostname)
            return False

        # HTTP port is slave port - 1000
        port -= 1000

        # Look at the slave's page
        url = "http://%s:%i/buildslaves/%s" % (host, port, slavename)
        log.info("Fetching slave page %s", url)
        data = urllib.urlopen(url + "?numbuilds=0").read()

        #if "not currently connected" in data:
            #log.error("%s isn't connected!", self.hostname)
            # reboot now?
            #return False

        if "Graceful Shutdown" not in data:
            log.error("no shutdown form for %s", self.hostname)
            return False

        log.info("Setting shutdown")
        data = urllib.urlopen(url + "/shutdown", "")
        return True

    def get_tacinfo(self):
        log.debug("Determining slave's master")
        data = self.cat_buildbot_tac()
        host = re.search('^buildmaster_host\s*=\s*["\'](.*)["\']', data, re.M)
        port = re.search('^port\s*=\s*(\d+)', data, re.M)
        slave = re.search('^slavename\s*=\s*["\'](.*)["\']', data, re.M)
        if host and port and slave:
            return host.group(1), int(port.group(1)), slave.group(1)

    def run_cmd(self, cmd):
        log.debug("Running %s", cmd)
        self.channel.sendall("%s\r\n" % cmd)
        data = self.wait()
        return data

class UnixishSlave(Slave):
    def _read(self):
        buf = []
        while self.channel.recv_ready():
            data = self.channel.recv(1024)
            if not data:
                break
            buf.append(data)
        buf = "".join(buf)

        # Strip out ANSI escape sequences
        # Setting position
        buf = re.sub('\x1b\[\d+;\d+f', '', buf)
        buf = re.sub('\x1b\[\d+m', '', buf)
        return buf

    def wait(self):
        buf = []
        while True:
            self.channel.sendall("\r\n")
            data = self._read()
            buf.append(data)
            if data.endswith(self.prompt) and not self.channel.recv_ready():
                break
            time.sleep(1)
        return "".join(buf)

    def find_buildbot_tacfiles(self):
        cmd = "ls -l %s/buildbot.tac*" % self.slavedir
        data = self.run_cmd(cmd)
        tacs = []
        exp = "\d+ %s/(buildbot\.tac(?:\.\w+)?)" % self.slavedir
        for m in re.finditer(exp, data):
            tacs.append(m.group(1))
        return tacs

    def cat_buildbot_tac(self):
        cmd = "cat %s/buildbot.tac" % self.slavedir
        return self.run_cmd(cmd)

    def tail_twistd_log(self, n=100):
        cmd = "tail -%i %s/twistd.log" % (n, self.slavedir)
        return self.run_cmd(cmd)

    def reboot(self):
        self.run_cmd("sudo reboot")

class OSXTalosSlave(UnixishSlave):
    prompt = "cltbld$ "
    slavedir = "/Users/cltbld/talos-slave"

class LinuxBuildSlave(UnixishSlave):
    prompt = "]$ "
    slavedir = "/builds/slave"

class OSXBuildSlave(UnixishSlave):
    prompt = "cltbld$ "
    slavedir = "/builds/slave"

class Win32Slave(Slave):
    def _read(self):
        buf = []
        while self.channel.recv_ready():
            data = self.channel.recv(1024)
            if not data:
                break
            buf.append(data)
        buf = "".join(buf)

        # Strip out ANSI escape sequences
        # Setting position
        buf = re.sub('\x1b\[\d+;\d+f', '', buf)
        return buf

    def wait(self):
        buf = []
        while True:
            self.channel.sendall("\r\n")
            data = self._read()
            buf.append(data)
            if data.endswith(">") and not self.channel.recv_ready():
                break
            time.sleep(1)
        return "".join(buf)

class Win32BuildSlave(Win32Slave):
    slavedir = "E:\\builds\\moz2_slave"

    def find_buildbot_tacfiles(self):
        cmd = "dir %s\\buildbot.tac*" % self.slavedir
        data = self.run_cmd(cmd)
        tacs = []
        for m in re.finditer("\d+ (buildbot\.tac(?:\.\w+)?)", data):
            tacs.append(m.group(1))
        return tacs

    def cat_buildbot_tac(self):
        cmd = "D:\\mozilla-build\\msys\\bin\\cat.exe %s\\buildbot.tac" % self.slavedir
        return self.run_cmd(cmd)

    def tail_twistd_log(self, n=100):
        cmd = "D:\\mozilla-build\\msys\\bin\\tail.exe -%i %s\\twistd.log" % (n, self.slavedir)
        return self.run_cmd(cmd)

    def reboot(self):
        self.run_cmd("shutdown -f -r -t 0")

class Win32TalosSlave(Win32Slave):
    slavedir = "C:\\talos-slave"

    def find_buildbot_tacfiles(self):
        cmd = "dir %s\\buildbot.tac*" % self.slavedir
        data = self.run_cmd(cmd)
        tacs = []
        for m in re.finditer("\d+ (buildbot\.tac(?:\.\w+)?)", data):
            tacs.append(m.group(1))
        return tacs

    def cat_buildbot_tac(self):
        cmd = "cat %s\\buildbot.tac" % self.slavedir
        return self.run_cmd(cmd)

    def tail_twistd_log(self, n=100):
        cmd = "tail -%i %s\\twistd.log" % (n, self.slavedir)
        return self.run_cmd(cmd)

    def reboot(self):
        self.run_cmd("shutdown -f -r -t 0")

def reboot_slave(hostname, username, password, graceful=True):
    if 'tegra' in hostname:
        log.info("Ignoring %s", hostname)
        return
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(WarningPolicy())
    client.connect(hostname, username=username, password=password, allow_agent=False)
    if 'w32-ix' in hostname or 'moz2-win32' in hostname or 'try-w32-' in hostname or 'win32-' in hostname:
        s = Win32BuildSlave(client, hostname)
    elif 'talos-r3-snow' in hostname:
        s = OSXTalosSlave(client, hostname)
    elif 'talos-r3-xp' in hostname:
        s = Win32TalosSlave(client, hostname)
    elif 'moz2-linux' in hostname or 'linux-ix' in hostname or 'try-linux' in hostname or 'linux64' in hostname:
        s = LinuxBuildSlave(client, hostname)
    elif 'try-mac' in hostname:
        s = OSXBuildSlave(client, hostname)
    else:
        log.error("Unknown slave type for %s", hostname)
        return
    s.wait()

    tacfiles = s.find_buildbot_tacfiles()
    if "buildbot.tac" not in tacfiles:
        log.info("Found these tacfiles: %s", tacfiles)
        for tac in tacfiles:
            m = re.match("^buildbot.tac.bug(\d+)$", tac)
            if m:
                log.info("Disabled by bug %s" % m.group(1))
                return
        log.info("Didn't find buildbot.tac")
        return

    data = s.tail_twistd_log(10)
    if "Stopping factory" in data:
        log.info("Looks like the slave isn't connected; rebooting!")
        s.reboot()
        return

    if not graceful:
        log.info("Rebooting!")
        s.reboot()
        return

    if not s.graceful_shutdown():
        log.info("graceful_shutdown failed; aborting")
        return
    log.info("Waiting for shutdown")
    count = 0
    while True:
        count += 1
        if count >= 30:
            log.info("Took too long to shut down; giving up")
            data = s.tail_twistd_log(10)
            log.info("last 10 lines are: %s", data)
            break

        data = s.tail_twistd_log(5)
        if "Main loop terminated" in data or "ProcessExitedAlready" in data:
            log.info("Rebooting!")
            s.reboot()
            break
        time.sleep(5)

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("paramiko.transport").setLevel(logging.WARNING)
    reboot_slave(*sys.argv[1:])
