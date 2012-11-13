import simplejson as json
import requests

class SlaveAllocAPI(object):
    def __init__(self, api="http://slavealloc.build.mozilla.org/api"):
        self.api = api

    def get_slave(self, slavename):
        r = requests.get(self.api + "/slaves/%s?byname=1" % slavename)
        return json.loads(r.content)

    def get_master_byid(self, master_id):
        r = requests.get(self.api + "/masters/%s" % master_id)
        return json.loads(r.content)

    def get_trust_byid(self, trust_id):
        r = requests.get(self.api + "/trustlevels/%s" % trust_id)
        return json.loads(r.content)

    def get_environ_byid(self, env_id):
        r = requests.get(self.api + "/environments/%s" % env_id)
        return json.loads(r.content)

    def put_slave(self, slave):
        requests.put(self.api + "/slaves/%i" % slave['slaveid'], data=json.dumps(slave))

    def get_slaves_by_master(self, mastername):
        r = requests.get(self.api + '/slaves')
        slaves = json.loads(r.content)
        retval = []
        for s in slaves:
            if s['current_master'] == mastername:
                retval.append(s)
        return retval
