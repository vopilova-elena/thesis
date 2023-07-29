import hashlib


class Hasher(object):
    @staticmethod
    def hash(data):
        h = hashlib.md5()
        h.update(repr(data).encode('utf-8'))
        return int(h.hexdigest(), 16)

    @staticmethod
    def get_hash_set(data_set):
        return frozenset(sorted([Hasher.hash(data) for data in data_set]))


