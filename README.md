# mod-redis-cluster-retention
retention module for Shinken Scheduler with **Redis Cluster** with 
[redis-py-cluster](https://github.com/Grokzen/redis-py-cluster)

# Features
* redis `key prefix`
  * if we use multiple Shinken setups with single Redis server, then we can 
  make sure that all keys from different Shinken setups can be absolutely 
  unique by using different prefixes.
  * Reason 
    * We can only make sure that only one `host_name + service_description` 
    can exist in a single Shinken setup. If we have many Shinken setups, we can 
    not make sure all `host_name + service_description` be unique.
  
* redis `expire time`
  * In case we change the configuration of Shinken, some service
  or host retention info will be deleted and then become useless. We can
  then add an expire time to each host or service info to make the useful
  retention persistent long by updating the expire time every time we save
  the retention info and the useless ones expired sometime and deleted
  automatically by Redis.
  
* redis `servers` and `password`
  * this is useful if your Redis cluster servers has a password and run in a 
  different port instead the default 6379. `servers` has the format of 
  `host1:port1, host2:port2,...,hostn:portn` 
  * If you do not specify `servers`, it will connect to Redis instance 
  running at `127.0.0.1` with default port `6379` with no password
  * If you do not specify `password`, it will connect to Redis 
  instance running at `servers` with  no password
  * If you specify `servers` and `password`, it will connect to Redis 
  instances running at `servers` with password `password`
  * If you specify `key_prefix`, it will add the `key_prefix` to the 
  beginning of the keys to be stored in Redis, Otherwise, Nothing will 
  prefix the keys.

# Usage 
Assuming Shinken is installed under standard directory
* install **redis-py-cluster==0.2.0**(this version is suggested to be used 
in production and we use the api exposed by redis-py-cluster 0.2.0)
* copy files under `module` directory to 
`/var/lib/shinken/modules/redis-cluster-retention`(you should create 
directory `redis-cluster-retention` first)
* copy files under `etc/module` directory to `/etc/shinken/modules/`
* to all files in `/etc/shinken/schedulers/*.cfg` append `modules` with 
`redis-cluster-retention`