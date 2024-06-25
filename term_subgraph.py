import sqlite3
from networkx import Graph
from decimal import Decimal
from datetime import datetime

from hasher import Hasher
from base_graph import BaseNodeType
class TermSubgraph(Graph):
    def load_from_db(self, fname):
        self.clear()

        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        print(datetime.now().strftime("%H:%M:%S"), 'load nodes...')
        cur.execute('SELECT * from nodes  where type=1')
        while True:
            row = cur.fetchone()
            if row == None:
                break
            hash_node = int(row[0])
            lemmas = frozenset(row[1].split())
            self.add_node(hash_node,
                          hash_set=Hasher.get_hash_set(lemmas),
                          lemmas=lemmas,
                          type=BaseNodeType(int(row[2])))
        print(datetime.now().strftime("%H:%M:%S"), 'load edges...')
        cur.execute('SELECT * from relations')
        while True:
            row = cur.fetchone()
            if row == None:
                break
            start_node = int(row[1])
            end_node = int(row[2])
            if self.has_node(start_node) and self.has_node(end_node):
                if self.has_edge(start_node, end_node):
                    self.edges[start_node, end_node]['weight'] += float(row[3])
                else:
                    self.add_edge(int(row[1]),
                                  int(row[2]),
                                  weight=float(row[3]))
        cur.close()
