from typing import Union

from redis import Redis, RedisCluster
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio import RedisCluster as AsyncRedisCluster
from redis.asyncio.cluster import ClusterNode as AsyncClusterNode
from redis.cluster import ClusterNode

from bingqilin.db.models import RedisDBConfig


RedisClientTypes = Union[Redis, RedisCluster, AsyncRedis, AsyncRedisCluster]


def make_redis_client(
    config: RedisDBConfig,
) -> RedisClientTypes:
    if config.nodes:
        if config.is_async:
            nodes = [AsyncClusterNode(**dict(node_conf)) for node_conf in config.nodes]
            return AsyncRedisCluster(startup_nodes=nodes)
        else:
            nodes = [ClusterNode(**dict(node_conf)) for node_conf in config.nodes]
            return RedisCluster(startup_nodes=nodes)
    else:
        redis_class = AsyncRedis if config.is_async else Redis
        return redis_class(
            host=config.host,
            port=config.port,
            db=config.db,
            username=config.username,
            password=config.password.get_secret_value() if config.password else None,
            unix_socket_path=config.unix_socket_path,
            ssl=config.ssl,
            **config.extra_data,
        )
