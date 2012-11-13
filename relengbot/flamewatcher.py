#!/usr/bin/env python
import simplejson
import time
import socket

import eventlet
from eventlet.green import urllib2
from eventlet.green import urllib

import logging
log = logging.getLogger(__name__)

import kombu, kombu.connection, kombu.messaging, kombu.entity
eventlet.monkey_patch()

SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(6)
results_str = ['SUCCESS', 'WARNINGS', 'FAILURE', 'SKIPPED', 'EXCEPTION', 'RETRY']

class FlameWatcher(object):
    def __init__(self, conn):
        self.conn = conn
        self.masters = None
        self.failures = []

    def run(self):
        eventlet.spawn_n(self._expire_masters)
        eventlet.spawn_n(self._report_stats)

        while True:
            try:
                chan = self.conn.channel()
                exchange = kombu.entity.Exchange(
                        'org.mozilla.exchange.build',
                        type='topic',
                        #durable=False,
                        #auto_delete=True,
                        )
                queue = kombu.entity.Queue(
                            name='catlee@mozilla.com|flamewatcher',
                            exchange=exchange,
                            durable=False,
                            routing_key='build.*.*.finished',
                            delivery_mode="transient",
                            #auto_delete=True,
                            )
                #queue.maybe_bind(chan)
                #queue.delete()
                consumer = kombu.messaging.Consumer(chan, queue)
                consumer.register_callback(self.handle_message)
                consumer.consume()

                self.conn.drain_events()
            except (socket.error,):
                eventlet.sleep(60)

    def _expire_masters(self):
        while True:
            eventlet.sleep(30)
            log.debug("Expiring masters")
            self.masters = None

    def _report_stats(self):
        while True:
            eventlet.sleep(30)

            # Count number of failures in past 5 minutes
            cutoff = time.time() - 300
            n = 0
            for t, msg in self.failures:
                if t <= cutoff:
                    msg.ack()
                    self.failures.remove( (t, msg) )
                else:
                    n += 1
            log.info("%i failures in past 5 minutes" % n)

    def _load_masters(self):
        masters = simplejson.load(urllib2.urlopen("http://hg.mozilla.org/build/tools/raw-file/default/buildfarm/maintenance/production-masters.json"))
        self.masters = masters

    def handle_message(self, body, message):
        if not self.masters:
            self._load_masters()

        if "-07" in body['_meta']['sent']:
            if not hasattr(self, 'bad_masters'):
                self.bad_masters = []

            if body['_meta']['master_name'] not in self.bad_masters:
                print body['_meta']['sent'], body['_meta']['master_name']
                self.bad_masters.append(body['_meta']['master_name'])

        results = body['payload']['results']
        if results in (SUCCESS, WARNINGS):
            message.ack()
            return

        self.failures.append( (time.time(), message) )
        master_host, master_dir = body['_meta']['master_name'].split(':')
        port = None
        for master in self.masters:
            if master['db_name'] == body['_meta']['master_name']:
                port = master['http_port']
                break
        else:
            log.info("Couldn't find master for %s", body['_meta'])
            return

        props = dict( (p[0], p[1]) for p in body['payload']['build']['properties'])
        if 'buildername' not in props:
            log.info("No buildername in %s", body)
            return

        buildername = urllib.quote(props['buildername'], "")
        buildnumber = props['buildnumber']

        url = "http://%(master_host)s:%(port)s/builders/%(buildername)s/builds/%(buildnumber)s" % locals()
        log.info("%s %s", results_str[results], url)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    conn = kombu.connection.BrokerConnection('pulse.mozilla.org', 'public', 'public', '/')
    W = FlameWatcher(conn)
    W.run()
