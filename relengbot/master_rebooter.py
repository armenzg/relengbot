#!/usr/bin/env python
"""
reboot all slaves attached to a master
"""
from lib.slavealloc import SlaveAllocAPI
from rebooter import reboot_slave
from getpass import getpass
import logging
log = logging.getLogger(__name__)
logging.basicConfig()

if __name__ == '__main__':
    slavealloc = SlaveAllocAPI()
    passwd = None

    for s in slavealloc.get_slaves_by_master('bm13-build1'):
        print "rebooting", s['name']
        if not passwd:
            passwd = getpass()

        try:
            reboot_slave(s['name'] + '.build.mozilla.org', 'cltbld', passwd, graceful=False)
        except:
            log.exception("problem rebooting %s", s['name'])
