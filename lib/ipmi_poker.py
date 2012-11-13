#!/usr/bin/env python
import socket
import time
import traceback

import requests

def reboot_ipmi(slavename):
    ip = socket.gethostbyname("%s-mgmt.build.mozilla.org" % slavename)

    print "logging into ipmi"
    r = requests.post("http://%s/cgi/login.cgi" % ip,
            data={
                'name': 'ADMIN',
                'pwd': 'ADMIN',
                })

    assert r.status_code == 200
    assert r.cookies

    # Push the button!
    # e.g.
    # http://10.12.48.105/cgi/ipmi.cgi?POWER_INFO.XML=(1%2C3)&time_stamp=Wed%20Mar%2021%202012%2010%3A26%3A57%20GMT-0400%20(EDT)
    print "pushing reset"
    r = requests.get("http://%s/cgi/ipmi.cgi" % ip,
            params={
                'POWER_INFO.XML': "(1,3)",
                'time_stamp': time.strftime("%a %b %d %Y %H:%M:%S"),
                },
            cookies = r.cookies
            )

    assert r.status_code == 200
    print "done"

if __name__ == '__main__':
    while True:
        slavename = raw_input("slavename: ")
        if not slavename:
            break

        slavename = slavename.split(".")[0]

        try:
            reboot_ipmi(slavename)
        except:
            traceback.print_exc()
