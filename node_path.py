class NodePath(object):
    def __init__(self):
        self.weight = 1
        self.relations = []

    def __str__(self):
        res = ''
        for rel in self.relations:
            if len(res) == 0:
                res = str(rel.start_node)
            res += "->(" + str(rel.type) + ") " + str(rel.end_node)
        return res + ' weight = ' + str(self.weight) + " edges = " + str(len(self.relations))


