from enum import IntEnum
from hasher import Hasher
from node_relation import NodeRelation, NodeRelationType


class NodeType(IntEnum):
    CANDIDATE = 0
    TERM = 1

    def __str__(self):
        return str(self.name)


class Node(object):
    def __init__(self, *args):
        self.type = None
        self.hash = None
        self.hash_set = None
        self.lemmas = None
        self.frequency = None
        self.idf = None
        self.word_count = None
        self.in_relations = None
        self.out_relations = None

        if len(args) == 2:
            self.init1(args[0], args[1])
        elif len(args) == 3:
            self.init2(args[0], args[1], args[2])

    def init1(self, lemmas, type):
        self.hash_set = Hasher.get_hash_set(lemmas)
        return self.init(Hasher.hash(self.hash_set), lemmas, type)

    def init2(self, hash_node, lemmas, type):
        return self.init(hash_node, lemmas, type)

    def init(self, hash, lemmas, type):
        self.hash = hash
        self.type = type
        self.lemmas = lemmas
        self.frequency = 0
        self.word_count = dict()
        self.out_relations = dict()
        self.in_relations = dict()
        for rel_type in NodeRelationType:
            self.word_count[rel_type] = 0
            self.out_relations[rel_type] = dict()
            self.in_relations[rel_type] = dict()

    def __str__(self):
        return str(list(self.lemmas))

    def get_out_relation(self, node, rel_type):
        if node.hash in self.out_relations[rel_type]:
            return self.out_relations[rel_type][node.hash]
        else:
            return None

    def get_out_relation_by_hash(self, node_hash, rel_type):
        if node_hash in self.out_relations[rel_type]:
            return self.out_relations[rel_type][node_hash]
        else:
            return None

    def add_out_relation(self, node, rel_type):
        rel = NodeRelation(self, node, rel_type, 1)
        self.out_relations[rel_type][node.hash] = rel
        node.in_relations[rel_type][self.hash] = rel
