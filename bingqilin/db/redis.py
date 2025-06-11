from typing import Union

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio import RedisCluster as AsyncRedisCluster
from redis.asyncio.cluster import ClusterNode as AsyncClusterNode
from redis.cluster import ClusterNode, RedisCluster

from bingqilin.db.models import RedisDBConfig

RedisClientTypes = Union[Redis, RedisCluster, AsyncRedis, AsyncRedisCluster]


def make_sync_redis_cluster(config: RedisDBConfig) -> RedisCluster:
    if not config.nodes:
        raise ValueError("A node configuration is required for RedisCluster.")

    nodes = [ClusterNode(**dict(node_conf)) for node_conf in config.nodes]
    return RedisCluster(startup_nodes=nodes)  # type: ignore


def make_async_redis_cluster(config: RedisDBConfig) -> AsyncRedisCluster:
    if not config.nodes:
        raise ValueError("A node configuration is required for RedisCluster.")

    nodes = [AsyncClusterNode(**dict(node_conf)) for node_conf in config.nodes]
    return AsyncRedisCluster(startup_nodes=nodes)  # type: ignore


def make_sync_redis_client(config: RedisDBConfig) -> Redis:
    return Redis(
        host=config.host,
        port=config.port,
        db=config.db,
        username=config.username,
        password=config.password.get_secret_value() if config.password else None,
        unix_socket_path=config.unix_socket_path,
        ssl=config.ssl,
        **config.extra_data,
    )


def make_async_redis_client(config: RedisDBConfig) -> AsyncRedis:
    return AsyncRedis(
        host=config.host,
        port=config.port,
        db=config.db,
        username=config.username,
        password=config.password.get_secret_value() if config.password else None,
        unix_socket_path=config.unix_socket_path,
        ssl=config.ssl,
        **config.extra_data,
    )


def make_redis_client(
    config: RedisDBConfig,
) -> RedisClientTypes:
    if config.nodes:
        if config.is_async:
            return make_async_redis_cluster(config)
        else:
            return make_sync_redis_cluster(config)
    else:
        if config.is_async:
            return make_async_redis_client(config)
        else:
            return make_sync_redis_client(config)
