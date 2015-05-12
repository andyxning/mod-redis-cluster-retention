# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015:
#    andy.xning@gmail.com

try:
    from rediscluster import RedisCluster
except ImportError:
    redis = None
import cPickle

from shinken.basemodule import BaseModule
from shinken.log import logger

properties = {
    'daemons': ['scheduler'],
    'type': 'redis_cluster_retention',
    'external': False,
    }


def get_instance(plugin):
    """
    Called by the plugin manager to get a broker
    """
    logger.debug("Get a redis retention scheduler "
                 "module for plugin %s" % plugin.get_name())
    if not redis:
        logger.error('Missing the module python-redis. Please install it.')
        raise Exception

    servers = getattr(plugin, 'servers', '127.0.0.1:6379')
    password = getattr(plugin, 'password', '')
    key_prefix = getattr(plugin, 'key_prefix', '')

    instance = RedisRetentionScheduler(plugin, servers, password, key_prefix)
    return instance


class RedisRetentionScheduler(BaseModule):

    def __init__(self, modconf, servers, password, port, key_prefix):
        BaseModule.__init__(self, modconf)
        self.servers = [dict(host=elt.strip().split(':')[0],
                             port=int(elt.strip().split(':')[1]))
                        for elt in servers.split(',')]
        self.password = password
        self.key_prefix = key_prefix

        self.mc = None

    def init(self):
        """
        Called by Scheduler to say 'let's prepare yourself guy'
        """
        logger.info("[RedisRetention] Initialization of the redis module")
        # self.return_queue = self.properties['from_queue']
        if self.password:
            self.mc = RedisCluster(startup_nodes=self.servers,
                                   password=self.password)
        else:
            self.mc = RedisCluster(startup_nodes=self.servers)

    def hook_save_retention(self, daemon):
        """
        main function that is called in the retention creation pass
        """
        logger.debug("[RedisRetention] asking me to update retention objects")

        all_data = daemon.get_retention_data()

        hosts = all_data['hosts']
        services = all_data['services']

        # Now the flat file method
        for h_name in hosts:
            h = hosts[h_name]
            key = "%s-HOST-%s" % (self.key_prefix, h_name) if \
                  self.key_prefix else "HOST-%s" % h_name
            val = cPickle.dumps(h)
            self.mc.set(key, val)

        for (h_name, s_desc) in services:
            s = services[(h_name, s_desc)]
            key = "%s-SERVICE-%s,%s" % (self.key_prefix, h_name, s_desc) if \
                  self.key_prefix else "SERVICE-%s,%s" % (h_name, s_desc)
            # space are not allowed in memcached key, so change it by
            # SPACEREPLACEMENT token
            key = key.replace(' ', 'SPACEREPLACEMENT')
            # print "Using key", key
            val = cPickle.dumps(s)
            self.mc.set(key, val)
        logger.info("Retention information updated in Redis")

    # Should return if it succeed in the retention load or not
    def hook_load_retention(self, daemon):

        # Now the new redis way :)
        logger.info("[RedisRetention] asking me to load retention objects")

        # We got list of loaded data from retention server
        ret_hosts = {}
        ret_services = {}

        # We must load the data and format as the scheduler want :)
        for h in daemon.hosts:
            key = "%s-HOST-%s" % (self.key_prefix, h.host_name) if \
                  self.key_prefix else "HOST-%s" % h.host_name
            val = self.mc.get(key)
            if val is not None:
                # redis get unicode, but we send string, so we are ok
                # val = str(unicode(val))
                val = cPickle.loads(val)
                ret_hosts[h.host_name] = val

        for s in daemon.services:
            key = "%s-SERVICE-%s,%s" % (self.key_prefix, s.host.host_name,
                                        s.service_description) if \
                  self.key_prefix else "SERVICE-%s,%s" % (s.host.host_name,
                                                          s.service_description)
            # space are not allowed in memcached key, so change it by
            # SPACEREPLACEMENT token
            key = key.replace(' ', 'SPACEREPLACEMENT')
            # print "Using key", key
            val = self.mc.get(key)
            if val is not None:
                # val = str(unicode(val))
                val = cPickle.loads(val)
                ret_services[(s.host.host_name, s.service_description)] = val

        all_data = {'hosts': ret_hosts, 'services': ret_services}

        # Ok, now come load them scheduler :)
        daemon.restore_retention_data(all_data)

        logger.info("[RedisRetention] Retention objects loaded successfully.")

        return True
