from enum import Enum


class NodeRelationType(Enum):
    DEF = 1
    GEN = 2
    ASS = 3
    def __str__(self):
        return str(self.name)


class NodeRelation(object):
    def __init__(self, start_node, end_node, relation_type, frequency):
        self.start_node = start_node
        self.end_node = end_node
        self.type = relation_type
        self.frequency = frequency
        self.tf = 0
        self.tf_idf = 0
        self.weight1 = self.weight2 = self.weight3 = 0

    def __str__(self):
        return str(self.type) + " (frequency: " + str(self.frequency) + ", weight: " + str(self.weight) + "): " \
               + str(self.start_node) + '=>' + str(self.end_node)
