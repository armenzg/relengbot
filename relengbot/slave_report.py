#!/usr/bin/env python

from lib.slavealloc import SlaveAllocAPI
from lib.bzapi import BzAPI

def run_report(slavename, sa, bz):
    print "checking slavealloc"
    slave = sa.get_slave(slavename)
    env_name = sa.get_environ_byid(slave['envid'])['name']
    print "notes:", slave['notes']
    print "enabled:", slave['enabled']
    print "environ:", env_name

    print
    print "recent jobs: https://build.mozilla.org/buildapi/recent/%s" % slavename
    print

    print "getting bug information"
    if slavename.startswith("moz2-darwin10"):
        alias = slavename[len("moz2-"):]
    else:
        alias = slavename
    slave_bug = bz.get_bug(alias, use_auth=True)

    if not slave_bug:
        print "no slave tracking bug"

    else:
        print "slave bug: https://bugzilla.mozilla.org/show_bug.cgi?id=%s" % slave_bug['id']
        print "status:", slave_bug['status']
        comments = bz.get_comments(slave_bug['id'])
        print "last comment:", comments['comments'][-1]

    print

if __name__ == '__main__':
    from getpass import getpass
    sa = SlaveAllocAPI()
    bz = BzAPI(api="https://api-dev.bugzilla.mozilla.org/1.0/")

    while True:
        slavename = raw_input("slavename: ")
        if not slavename:
            break

        slavename = slavename.split(".")[0]

        run_report(slavename, sa, bz)
