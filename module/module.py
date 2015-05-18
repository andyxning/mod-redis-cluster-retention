# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2015:
#    andy.xning@gmail.com
#
# This file is part of Shinken.
#
# Shinken is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shinken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

try:
    from rediscluster import RedisCluster
except ImportError:
    RedisCluster = None
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
    logger.debug('Get a redis cluster retention scheduler '
                 'module for plugin %s' % plugin.get_name())
    if not RedisCluster:
        logger.error('Missing redis cluster client redis-py-cluster(0.2.0). '
                     'Please install it.')
        raise Exception

    servers = getattr(plugin, 'servers', '127.0.0.1:6379')
    password = getattr(plugin, 'password', '')
    key_prefix = getattr(plugin, 'key_prefix', '')
    expire_time = int(getattr(plugin, 'expire_time', 0))

    instance = RedisClusterRetentionScheduler(plugin, servers, password,
                                              key_prefix, expire_time)
    return instance


class RedisClusterRetentionScheduler(BaseModule):

    def __init__(self, modconf, servers, password, key_prefix, expire_time):
        BaseModule.__init__(self, modconf)
        self.servers = [dict(host=elt.strip().split(':')[0],
                             port=int(elt.strip().split(':')[1]))
                        for elt in servers.split(',')]
        self.password = password
        self.key_prefix = key_prefix
        self.expire_time = expire_time

        self.rc = None

    def init(self):
        """
        Called by Scheduler to say 'let's prepare yourself guy'
        """
        logger.info('[RedisClusterRetention] Initialization of the redis '
                    'module')
        if self.password:
            self.rc = RedisCluster(startup_nodes=self.servers,
                                   password=self.password)
        else:
            self.rc = RedisCluster(startup_nodes=self.servers)

    def _get_host_key(self, h_name):
        host_key = '%s-HOST-%s' % (self.key_prefix, h_name) \
                   if self.key_prefix else 'HOST-%s' % h_name
        return host_key

    def _get_service_key(self, h_name, s_name):
        service_key = '%s-SERVICE-%s,%s' % (self.key_prefix, h_name, s_name)\
                      if self.key_prefix \
                      else 'SERVICE-%s,%s' % (h_name, s_name)
        return service_key

    def hook_save_retention(self, daemon):
        """
        main function that is called in the retention creation pass
        """
        logger.debug('[RedisClusterRetention] asking me to update retention '
                     'objects')

        all_data = daemon.get_retention_data()

        hosts = all_data['hosts']
        services = all_data['services']

        # Now the flat file method
        for h_name in hosts:
            h = hosts[h_name]
            key = self._get_host_key(h_name)
            val = cPickle.dumps(h)
            if self.expire_time:
                self.rc.set(key, val, ex=self.expire_time)
            else:
                self.rc.set(key, val)

        for (h_name, s_desc) in services:
            s = services[(h_name, s_desc)]
            key = self._get_service_key(h_name, s_desc)
            val = cPickle.dumps(s)
            if self.expire_time:
                self.rc.set(key, val, ex=self.expire_time)
            else:
                self.rc.set(key, val)
        logger.info('Retention information updated in Redis')

    # Should return if it succeed in the retention load or not
    def hook_load_retention(self, daemon):

        # Now the new redis way :)
        logger.info('[RedisClusterRetention] asking me to load retention '
                    'objects')

        # We got list of loaded data from retention server
        ret_hosts = {}
        ret_services = {}

        # We must load the data and format as the scheduler want :)
        for h in daemon.hosts:
            key = self._get_host_key(h.host_name)
            val = self.rc.get(key)
            if val is not None:
                val = cPickle.loads(val)
                ret_hosts[h.host_name] = val

        for s in daemon.services:
            key = self._get_service_key(s.host.host_name,
                                        s.service_description)
            val = self.rc.get(key)
            if val is not None:
                val = cPickle.loads(val)
                ret_services[(s.host.host_name, s.service_description)] = val

        all_data = {'hosts': ret_hosts, 'services': ret_services}

        # Ok, now come load them scheduler :)
        daemon.restore_retention_data(all_data)

        logger.info('[RedisClusterRetention] Retention objects loaded '
                    'successfully.')

        return True
