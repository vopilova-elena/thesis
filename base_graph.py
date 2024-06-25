import sqlite3
from pathlib import Path
from networkx import MultiDiGraph
from enum import IntEnum
from decimal import Decimal
from datetime import datetime
import xml.etree.cElementTree as ET

from hasher import Hasher

ATTENUATION = Decimal(0.9)
MIN_PATH_WEIGHT = Decimal(0.005)


class BaseNodeType(IntEnum):
    CANDIDATE = 0
    TERM = 1

    def __str__(self):
        return str(self.name)


class BaseNodeRelationType(IntEnum):
    DEF = 1
    GEN = 2
    ASS = 3

    def __str__(self):
        return str(self.name)


class BaseGraph(MultiDiGraph):
    def load_from_db(self, fname, detailed=False):
        self.clear()

        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        print(datetime.now().strftime("%H:%M:%S"), 'load nodes...')
        cur.execute('SELECT * from nodes')
        while True:
            row = cur.fetchone()
            if row == None:
                break
            hash_node = int(row[0])
            lemmas = frozenset(row[1].split())
            if detailed:
                self.add_node(hash_node,
                              hash_set=Hasher.get_hash_set(lemmas),
                              lemmas=lemmas,
                              type=BaseNodeType(int(row[2])),
                              centrality=Decimal.normalize(round(Decimal(row[3]), 6)),
                              len_definition=int(row[4]),
                              len_content=int(row[5]),
                              idf=Decimal.normalize(round(Decimal(row[6]), 6)))
            else:
                self.add_node(hash_node,
                              hash_set=Hasher.get_hash_set(lemmas),
                              lemmas=lemmas,
                              type=BaseNodeType(int(row[2])),
                              centrality=Decimal.normalize(round(Decimal(row[3]), 6)))
        print(datetime.now().strftime("%H:%M:%S"), 'load relations...')
        cur.execute('SELECT * from relations')
        while True:
            row = cur.fetchone()
            if row == None:
                break
            rel_type = BaseNodeRelationType(int(row[0]))
            if detailed:
                self.add_edge(int(row[1]),
                              int(row[2]),
                              type=rel_type,
                              weight=Decimal.normalize(round(Decimal(row[3]), 6)),
                              frequency=int(row[4]),
                              tf=Decimal.normalize(round(Decimal(row[5]), 6)),
                              tf_idf=Decimal.normalize(round(Decimal(row[6]), 6)))
            else:
                self.add_edge(int(row[1]),
                              int(row[2]),
                              type=rel_type,
                              weight=Decimal.normalize(round(Decimal(row[3]), 6)))
        cur.close()

    def save_to_db(self, fname, duplicate_edge=True, only_terms=False, detailed=False):
        p = Path(fname)
        if not Path(p.parents[0]).exists():
            Path(p.parents[0]).mkdir(parents=True)

        conn = sqlite3.connect(fname)
        cur = conn.cursor()

        cur.execute('DROP TABLE IF EXISTS nodes')
        cur.execute('DROP TABLE IF EXISTS relations')
        conn.commit()

        if detailed:
            cur.execute('CREATE TABLE nodes ('
                        'hash TEXT NOT NULL UNIQUE,'
                        'lemmas	TEXT,'
                        'type INTEGER,'
                        'centrality REAL,'
                        'len_definition INTEGER,'
                        'len_content INTEGER,'
                        'idf REAL,'
                        'PRIMARY KEY(hash));')
            cur.execute('CREATE TABLE relations ('
                        'type INTEGER NOT NULL,'
                        'hash_start_node TEXT NOT NULL,'
                        'hash_end_node TEXT NOT NULL,'
                        'weight REAL,'
                        'frequency INTEGER,'
                        'tf	REAL,'
                        'tf_idf REAL);')
        else:
            cur.execute('CREATE TABLE nodes ('
                        'hash TEXT NOT NULL UNIQUE,'
                        'lemmas	TEXT,'
                        'type INTEGER,'
                        'centrality REAL,'
                        'PRIMARY KEY(hash));')
            cur.execute('CREATE TABLE relations ('
                        'type INTEGER NOT NULL,'
                        'hash_start_node TEXT NOT NULL,'
                        'hash_end_node TEXT NOT NULL,'
                        'weight REAL);')

        cur.execute('CREATE INDEX hash_start_node ON relations (hash_end_node ASC);')
        cur.execute('CREATE INDEX hash_end_node ON relations (hash_end_node ASC);')
        conn.commit()

        for key, value in self.nodes.items():
            if only_terms and value['type'] == BaseNodeType.CANDIDATE:
                continue
            if detailed:
                cur.execute("INSERT INTO nodes VALUES(?, ?, ?, ?, ?, ?, ?);",
                            (str(key),
                             ' '.join(value['lemmas']),
                             int(value['type']),
                             str(value['centrality']),
                             value['len_definition'],
                             value['len_content'],
                             str(value['idf'])))
            else:
                cur.execute("INSERT INTO nodes VALUES(?, ?, ?, ?);",
                            (str(key),
                             ' '.join(value['lemmas']),
                             int(value['type']),
                             str(value['centrality'])))

            for nbr, nbr_edges in self[key].items():
                if only_terms and self.nodes[nbr]['type'] == BaseNodeType.CANDIDATE:
                    continue

                if duplicate_edge:
                    for edge in nbr_edges.values():
                        if detailed:
                            cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?, ?, ?, ?);",
                                        (int(edge['type']),
                                         str(key),
                                         str(nbr),
                                         str(edge['weight']),
                                         edge['frequency'],
                                         str(edge['tf']),
                                         str(edge['tf_idf'])))
                        else:
                            cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?);",
                                        (int(edge['type']),
                                         str(key),
                                         str(nbr),
                                         str(edge['weight'])))
                else:
                    sorted_nbr_edges = sorted(nbr_edges.values(), key=lambda x: -x['weight'])
                    if detailed:
                        cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?, ?, ?, ?);",
                                    (int(sorted_nbr_edges[0]['type']),
                                     str(key),
                                     str(nbr),
                                     str(sorted_nbr_edges[0]['weight']),
                                     sorted_nbr_edges[0]['frequency'],
                                     str(sorted_nbr_edges[0]['tf']),
                                     str(sorted_nbr_edges[0]['tf_idf'])))
                    else:
                        cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?);",
                                    (int(sorted_nbr_edges[0]['type']),
                                     str(key),
                                     str(nbr),
                                     str(sorted_nbr_edges[0]['weight'])))
        conn.commit()
        cur.close()

    def load_from_xml(self, fname):
        self.clear()

        tree = ET.parse(fname)
        root = tree.getroot()

        print('load nodes...')
        for node in root.iter('node'):
            self.add_node(int(node.get('id')),
                          hash_set=Hasher.get_hash_set(node.text),
                          lemmas=frozenset(node.text.split()),
                          type=BaseNodeType[node.get('type')],
                          centrality=0)

        print('load relations...')
        for edge in root.iter('edges'):
            self.add_edge(int(edge.get('src')),
                          int(edge.get('dst')),
                          type=BaseNodeRelationType[edge.get('type')],
                          weight=Decimal(edge.get('weight')))

    def save_to_xml(self, fname, dublicate_edge=False, only_terms=False, detailed=False):
        root = ET.Element('graph')
        nodes = ET.SubElement(root, 'nodes')
        edges = ET.SubElement(root, 'edges')

        for key, value in self.nodes.items():
            if only_terms and value['type'] == BaseNodeType.CANDIDATE:
                continue
            if detailed:
                ET.SubElement(nodes, 'node',
                              id=str(key),
                              type=str(value['type']),
                              centrality=str(value['centrality']),
                              len_definition=str(value['len_definition']),
                              len_content=str(value['len_content']),
                              idf=str(value['idf'])).text = ' '.join(value['lemmas'])
            else:
                ET.SubElement(nodes, 'node',
                              id=str(key),
                              type=str(value['type'])).text = ' '.join(value['lemmas'])

            for nbr, nbr_edges in self[key].items():
                if only_terms and self.nodes[nbr]['type'] == BaseNodeType.CANDIDATE:
                    continue

                if dublicate_edge:
                    for edge in nbr_edges.values():
                        if detailed:
                            ET.SubElement(edges, 'edge',
                                          src=str(key),
                                          dst=str(nbr),
                                          type=str(edge['type']),
                                          weight=str(edge['weight']),
                                          frequency=str(edge['frequency']),
                                          tf=str(edge['tf']),
                                          tf_idf=str(edge['tf_idf']))
                        else:
                            ET.SubElement(edges, 'edge',
                                          src=str(key),
                                          dst=str(nbr),
                                          type=str(edge['type']),
                                          weight=str(edge['weight']))
                else:
                    sorted_nbr_edges = sorted(nbr_edges.values(),
                                              key=lambda x: -x['weight'])
                    if detailed:
                        ET.SubElement(edges, 'edge',
                                      src=str(key),
                                      dst=str(nbr),
                                      type=str(sorted_nbr_edges[0]['type']),
                                      weight=str(sorted_nbr_edges[0]['weight']),
                                      frequency=str(sorted_nbr_edges[0]['frequency']),
                                      tf=str(sorted_nbr_edges[0]['tf']),
                                      tf_idf=str(sorted_nbr_edges[0]['tf_idf']))
                    else:
                        ET.SubElement(edges, 'edge',
                                      src=str(key),
                                      dst=str(nbr),
                                      type=str(sorted_nbr_edges[0]['type']),
                                      weight=str(sorted_nbr_edges[0]['weight']))

        tree = ET.ElementTree(root)
        ET.indent(tree, '  ')
        tree.write(fname, 'utf-8')

    def get_node_neighborhood(self, node):
        neighbor_paths = []
        curr_path = {'edges': [], 'weight': 1}
        self.get_node_neighborhood_recur(node, neighbor_paths, curr_path)
        return neighbor_paths
        #

    def get_node_neighborhood_recur(self, node, paths, curr_path):
        if curr_path['weight'] < MIN_PATH_WEIGHT:
            return
        if len(curr_path['edges']) > 0:
            paths.append(curr_path)
        for nbr, nbr_edges in self[node].items():
            max_weight = max([e['weight'] for e in nbr_edges.values()])
            new_path = {'edges': curr_path['edges'].copy(),
                        'weight': round(curr_path['weight'] * max_weight * ATTENUATION, 6)}
            new_path['edges'].append((node, nbr, max_weight))
            self.get_node_neighborhood_recur(nbr, paths, new_path)

# GG = BaseGraph()
# print(datetime.now().strftime('%H:%M:%S'))
# GG.load_from_db('_db\\semantic_graph.db')
# print(GG.number_of_nodes(), GG.number_of_edges())
# print(datetime.now().strftime('%H:%M:%S'))
# #GG.save_to_xml('_out\\filename.xml')
# h = Hasher.hash(Hasher.get_hash_set('обыкновенный дифференциальный уравнение'.split()))
# nn = GG.get_node_neighborhood(h)
# k=0
# for path in nn:
#     print(GG.nodes[h]['lemmas'], end='')
#     for e in path['edges']:
#         print('->', GG.nodes[e[1]]['lemmas'], end='')
#     print(path['weight'])

# # рисуем граф и отображаем его
# nx.draw(G, with_labels=False)
# plt.show()
