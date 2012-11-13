#!/usr/bin/env python
"""
adds slaves to reboot bugs
"""
#import socket
import dns.resolver
from lib.slavealloc import SlaveAllocAPI
from lib.bzapi import BzAPI

def check_slave(slavealloc, slavename):
    """
    Checks that a slave is ok to be bugged about according to slavealloc.

    This means that it should have no notes on it, and should be a production or try box

    Returns True if a slave is ok to be bugged about
    """
    print "checking slavealloc"
    slave = slavealloc.get_slave(slavename)

    if slave['notes']:
        print "non-empty notes in slavealloc, you're on your own!"
        print slave['notes']
        return False

    if not slave['enabled']:
        print 'slave is disabled in slavealloc'
        return False

    env = slavealloc.get_environ_byid(slave['envid'])
    if not env['name'] == 'prod':
        print 'slave env is not prod:', env['name']
        return False

    print "slavealloc OK"
    return True

def to_fqdn(slavename):
    return str(dns.resolver.query(slavename + ".build.mozilla.org").canonical_name)
    #return socket.getfqdn(slavename + ".build.mozilla.org")

def get_reboots_bug(slavename, bzapi):
    fqdn = to_fqdn(slavename)
    dc = fqdn.split(".")[2]

    bugname = "reboots-%s" % dc

    print "getting bug", bugname
    bug = bzapi.get_bug(bugname, use_auth=True)
    return bug

def get_slave_bug(slavename, bzapi):
    bugname = slavename
    if 'darwin10' in slavename and slavename.startswith("moz2-"):
        bugname = slavename[len("moz2-"):]

    print "getting bug", bugname
    bug = bzapi.get_bug(bugname, use_auth=True)
    return bug

def create_reboots_bug(slavename, bzapi):
    fqdn = to_fqdn(slavename)
    dc = fqdn.split(".")[2]

    bugname = "reboots-%s" % dc
    bug = {
            'product': 'mozilla.org',
            'component': 'Server Operations: DCOps',
            'alias': bugname,
            'summary': bugname,
            'comment': 'stuff to reboot',
            'op_sys': 'All',
            'platform': 'All',
            'version': 'other',
            'whiteboard': '[buildduty]',
            }
    return bzapi.create_bug(bug)

def create_slave_bug(slavename, bzapi):
    alias = slavename
    if 'darwin10' in slavename and slavename.startswith("moz2-"):
        alias = slavename[len("moz2-"):]

    bug = {
            'product': 'mozilla.org',
            'component': 'Release Engineering: Machine Management',
            'alias': alias,
            'summary': "%s problem tracking" % slavename,
            'comment': 'stuff to reboot',
            'op_sys': 'All',
            'platform': 'All',
            'version': 'other',
            'whiteboard': '[buildduty]',
            }
    return bzapi.create_bug(bug)

def bug_slave(slavename, bzapi, slavealloc):
    """
    Adds slavename to the reboots bug for its location.

    If slavealloc is set, first check to see if the slave has any notes, and is
    in the right environment.
    """
    if slavealloc and not check_slave(slavealloc, slavename):
        print "check_slave failed, not bugging about slave"
        return False

    slave_bug = get_slave_bug(slavename, bzapi)
    if not slave_bug:
        print "no slave bug! creating one"
        create_slave_bug(slavename, bzapi)
        slave_bug = get_slave_bug(slavename, bzapi)
        assert slave_bug

    reboots_bug = get_reboots_bug(slavename, bzapi)
    if not reboots_bug:
        print "no reboots bug! filing one..."
        reboots_bug = create_reboots_bug(slavename, bzapi)
    elif reboots_bug['status'] == 'RESOLVED':
        print 'reboots bug is closed! removing alias'
        bzapi.save_bug(reboots_bug['id'], {
            'alias': None,
            'update_token': reboots_bug['update_token'],
            })
        print "filing new reboots bug"
        reboots_bug = create_reboots_bug(slavename, bzapi)
    print reboots_bug['id']

    if slave_bug['status'] == 'RESOLVED':
        print "re-opening slave bug"
        slave_bug['status'] = 'REOPENED'

    print "adding slave to depend on reboots bug"
    if 'depends_on' not in slave_bug:
        slave_bug['depends_on'] = [reboots_bug['id']]
    else:
        if str(reboots_bug['id']) in slave_bug['depends_on']:
            print "already in reboots bug!"
        elif isinstance(slave_bug['depends_on'], basestring):
            slave_bug['depends_on'] = [slave_bug['depends_on'], reboots_bug['id']]
        else:
            slave_bug['depends_on'].append(reboots_bug['id'])

    bzapi.save_bug(slave_bug['id'], {
        'depends_on': slave_bug['depends_on'],
        'update_token': slave_bug['update_token'],
        'status': slave_bug['status'],
        })
    print "done"

if __name__ == '__main__':
    from getpass import getpass
    import logging
    logging.basicConfig(level=logging.WARN)
    slavealloc = SlaveAllocAPI()
    bzapi = BzAPI(username='catlee@mozilla.com', password=getpass("bugzilla password: "), api="https://api-dev.bugzilla.mozilla.org/1.0/")

    while True:
        slavename = raw_input("slavename: ")
        if not slavename:
            break

        try:
            bug_slave(slavename, bzapi, slavealloc)
        except:
            logging.exception("problem bugging about %s", slavename)
