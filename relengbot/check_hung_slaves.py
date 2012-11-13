#!/usr/bin/python
try:
    import simplejson as json
except ImportError:
    import json

import pytz
import requests
from datetime import datetime, timedelta
import time
import re
import urllib
import logging
from collections import namedtuple
BuildbotSlave = namedtuple("BuildbotSlave", "name connected idle last_heard")

logging.getLogger('requests').setLevel(logging.WARN)

log = logging.getLogger()

def parse_slaves_page(data):
    retval = []
    slaveLine = re.compile("href=\"buildslaves/([A-Za-z].*?)\"")
    statusLine = re.compile("td class=\"(offline|idle|building)\"")
    lastHeardLine = re.compile("<td>.*<small>\((.*)\)</small></td>")

    curSlave = None
    lastHeard = None
    for line in data.split("\n"):
        m = slaveLine.search(line)
        if m:
            curSlave = m.group(1)
            continue
        if not curSlave:
            continue
        m = lastHeardLine.search(line)
        if m:
            lastHeard = datetime.strptime(m.group(1), "%Y-%b-%d %H:%M:%S")

        m = statusLine.search(line)
        if m:
            status = m.group(1)
            if status == 'offline':
                retval.append(BuildbotSlave(curSlave, False, False, lastHeard))
            elif status == 'idle':
                retval.append(BuildbotSlave(curSlave, True, True, lastHeard))
            elif status == 'building':
                retval.append(BuildbotSlave(curSlave, True, False, lastHeard) )
            else:
                raise ValueError("Unknown status line: %s" % line)
            curSlave = None
            lastHeard = None

    return retval

def get_masters(url):
    log.info("Getting master list from %s", url)
    return json.load(urllib.urlopen(url))

def get_slaves(url):
    log.info("Getting slave info from %s", url)
    try:
        data = urllib.urlopen(url).read()
        return parse_slaves_page(data)
    except:
        log.error("Error loading %s", url)
        return []

def get_slavealloc_slaves(url="http://slavealloc.build.mozilla.org/api/slaves"):
    data = requests.get(url).content
    slaves = json.loads(data)
    return slaves

def get_slavealloc_masters(url="http://slavealloc.build.mozilla.org/api/masters"):
    data = requests.get(url).content
    return json.loads(data)

def get_last_build(slavename):
    req = requests.get("http://cruncher.build.mozilla.org/buildapi/recent/%s" % slavename, params={'format': 'json', 'numbuilds': '1'})
    assert req.status_code == 200, req
    data = json.loads(req.content)
    if data:
        return data[0]['starttime']
    return None

UTC = pytz.timezone('UTC')
def now(tz):
    retval = datetime.utcfromtimestamp(time.time())
    retval = tz.normalize(UTC.localize(retval).astimezone(tz))
    return retval

class Slave(object):
    def __init__(self, name):
        self.name = name
        self.buildbot_data = {}
        self.slavealloc_data = None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    masters_url = "http://hg.mozilla.org/build/tools/raw-file/default/buildfarm/maintenance/production-masters.json"

    server_tz = pytz.timezone('US/Pacific')

    # Mapping of slave names to Slave objects
    slaves = {}

    # Check slavealloc
    log.info("Getting slavealloc data")
    slavealloc_masters = dict((m['masterid'],m) for m in get_slavealloc_masters())
    for s in get_slavealloc_slaves():
        sl = slaves.setdefault(s['name'], Slave(s['name']))
        sl.slavealloc_data = s

        if not s['enabled']:
            continue
        if s['notes']:
            log.info("skipping %s with non-emtpy notes: %s", s['name'], s['notes'])
            continue
        if s['trustlevel'] == 'dev':
            log.info("skipping dev/pp slave %s", s['name'])
            continue

        #sl.buildapi_lastbuild = get_last_build(s['name'])
        #if sl.buildapi_lastbuild:
            #sl.buildapi_lastbuild = datetime.utcfromtimestamp(sl.buildapi_lastbuild)

    log.info("Getting list of masters")
    masters = get_masters(masters_url)

    for master in masters:
        if not master['enabled']:
            continue
        if 'http_port' not in master:
            continue
        buildslaves_url = "http://%s:%i/buildslaves?no_builders=1" % (master['hostname'], master['http_port'])
        master_slaves = get_slaves(buildslaves_url)
        for s in master_slaves:
            sl = slaves.setdefault(s.name, Slave(s.name))
            sl.buildbot_data[master['hostname'], master['http_port']] = s

    for name, s in slaves.items():
        print name
        print "\t", s.buildbot_data
        print "\t", s.slavealloc_data

    while False:
            if 'tegra' in s.name:
                continue
            if not s.connected:
                continue
            if s.idle:
                continue
            if not s.last_heard:
                log.warn("No last heard info from %s", s.name)
                continue

            delta = now(server_tz) - server_tz.localize(s.last_heard)
            if delta > timedelta(minutes=90):
                log.warn("%s is hung (last heard from %s ago)", s.name, delta)
