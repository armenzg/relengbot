import requests
try:
    import simplejson as json
except ImportError:
    import json

import sys
import logging
log = logging.getLogger(__name__)

class BzAPI(object):
    def __init__(self, api,
            username=None, password=None):
        self.api = api
        self.username = username
        self.password = password

    def request(self, path, data=None, method=None, params=None, use_auth=False):
        url = self.api + path
        if data:
            data = json.dumps(data)

        if use_auth and self.username and self.password:
            if not params:
                params = {}
            else:
                params = params.copy()
            params['username'] = self.username
            params['password'] = self.password

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        method = method or "GET"

        log.debug("%s %s %s", method, url, data)
        req = requests.request(method, url, headers=headers, data=data, params=params)

        try:
            return json.loads(req.content)
        except:
            log.exception("couldn't load data from %s (%s):\n%s", req, url, req.content)

    def check_request(self, *args, **kw):
        result = self.request(*args, **kw)
        assert not result.get('error'), result
        return result

    def get_bug(self, bug_num, use_auth=False):
        try:
            bug = self.request("/bug/%s" % bug_num, use_auth=use_auth)
            if bug.get('error') == True:
                return None
            return bug
        except KeyboardInterrupt:
            raise
        except:
            log.exception("Error fetching bug %s" % bug_num)
            return None

    def get_comments(self, bug_num):
        try:
            comments = self.request("/bug/%s/comment" % bug_num)
            return comments
        except KeyboardInterrupt:
            raise
        except:
            log.exception("Error fetching comments for bug %s" % bug_num)
            return None

    def add_comment(self, bug_num, message):
        assert self.username and self.password
        self.check_request("/bug/%s/comment" % bug_num,
                {"text": message, "is_private": False}, "POST")

    def create_bug(self, bug):
        assert self.username and self.password
        return self.check_request("/bug", bug, "POST", use_auth=True)

    def save_bug(self, bug_id, params):
        assert self.username and self.password
        return self.check_request("/bug/%s" % bug_id, data=params, method="PUT", use_auth=True)

if __name__ == '__main__':
    logging.basicConfig()
    api = "https://api-dev.bugzilla.mozilla.org/1.0/"
    api = "https://api-dev.bugzilla.mozilla.org/test/1.0/"
    bz = BzAPI(api, username="catlee@mozilla.com", password="asdfkjsadf;laskjfd;salkdjf")
    bug = bz.get_bug("reboots-scl1")
    if not bug:
        bug = {
                #'product': 'mozilla.org',
                'product': 'FoodReplicator',
                #'component': 'Server Operations: RelEng',
                'component': 'Salt',
                'alias': 'reboots-scl1',
                'summary': 'reboots-scl1',
                'comment': 'reboot it!',
                'op_sys': 'All',
                'platform': 'All',
                'version': '1.0',
              }
        r = bz.create_bug(bug)
        print r
    else:
        bug_id = bug['id']
        print bz.get_comments(bug_id)
