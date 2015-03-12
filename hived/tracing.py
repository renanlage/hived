from threading import local
import uuid


_local = local()


def generate_id():
    return str(uuid.uuid4())


def get_id():
    return getattr(_local, 'tracing_id', None)


def set_id(id_):
    _local.tracing_id = id_ or generate_id()