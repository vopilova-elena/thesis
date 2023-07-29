from math import log, log2, log10, pow
from node import NodeType, Node
from node_relation import NodeRelationType, NodeRelation
from node_path import NodePath
from decimal import Decimal
from ngram_helper import NGramHelper
from hasher import Hasher
import sqlite3

ATTENUATION = Decimal(0.1)
MIN_PATH_WEIGHT = Decimal(0.005)


class TermGraph(object):
    def __init__(self):
        self.hash_terms = dict()
        self.term_count = 0

    def load_from_db(self, fname):
        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        cur.execute("SELECT * from nodes")
        print("load nodes...")
        rows = cur.fetchall()
        for row in rows:
            hash_node = int(row[0])
            self.hash_terms[hash_node] = Node(hash_node, frozenset(row[1].split()), NodeType(int(row[2])))
        cur.execute("SELECT * from relations")
        rows = cur.fetchall()
        print("load relations...")
        for row in rows:
            rel_type = NodeRelationType(int(row[0]))
            h = int(row[1])
            if h in self.hash_terms:
                start_node = self.hash_terms[h]
            else:
                print("start", h)
            h = int(row[2])
            if h in self.hash_terms:
                end_node = self.hash_terms[int(row[2])]
            else:
                print("end", h)
            start_node.add_out_relation(end_node, rel_type)
            rel = start_node.get_out_relation(end_node, rel_type)
            rel.weight1, rel.weight2, rel.weight3 = round(Decimal(row[6]), 6), round(Decimal(row[7]), 6), round(Decimal(row[8]), 6)
        cur.close()

    def save_to_db(self, fname):
        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        cur.execute("DELETE FROM nodes")
        cur.execute("DELETE FROM relations")
        conn.commit()
        for key, value in self.hash_terms.items():
            if len(value.hash_set) == 1:
                if value.idf is None:
                    value.idf = 0
                cur.execute("INSERT INTO nodes VALUES(?, ?, ?, ?, ?, ?);",
                            (str(value.hash), ' '.join(value.lemmas), int(value.type),
                             value.word_count[NodeRelationType.ASS], value.frequency, str(value.idf)))
            else:
                cur.execute("INSERT INTO nodes VALUES(?, ?, ?, ?, ?, null);",
                            (str(value.hash), ' '.join(value.lemmas), int(value.type),
                             value.word_count[NodeRelationType.ASS], value.frequency))
            for rel_type in NodeRelationType:
                for h, rel in value.out_relations[rel_type].items():
                    if (rel_type == NodeRelationType.ASS) and (len(rel.end_node.hash_set) == 1):
                        cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?);",
                                    (rel_type.value,
                                     str(rel.start_node.hash), str(rel.end_node.hash),
                                     rel.frequency, str(rel.tf), str(rel.tf_idf),
                                     str(rel.weight1), str(rel.weight2), str(rel.weight3)))
                    else:
                        cur.execute("INSERT INTO relations VALUES(?, ?, ?, ?, null, null, ?, ?, ?);",
                                    (rel_type.value, str(rel.start_node.hash), str(rel.end_node.hash), rel.frequency,
                                     str(rel.weight1), str(rel.weight2), str(rel.weight3)))

        conn.commit()
        cur.close()

    def add_gen_relations(self):
        for key, value in self.hash_terms.items():
            if value.type == NodeType.CANDIDATE:
                continue
            for lemmas in NGramHelper.n_grams_lemmas(list(value.lemmas), len(value.lemmas) - 1):
                h = Hasher.hash(Hasher.get_hash_set(lemmas))
                if h in self.hash_terms:
                    value.add_out_relation(self.hash_terms[h], NodeRelationType.GEN)

    def get_node_idf(self, node):
        c = 0
        for h, in_rel in node.in_relations[NodeRelationType.ASS].items():
            if in_rel.start_node.word_count[NodeRelationType.ASS] > 0: # ??? зачем?
                c += 1
        try:
            return round(Decimal(log10(self.term_count / c)), 6)
        except ZeroDivisionError:
            print("error calc idf:" + str(node.lemmas))
            return 0

    def get_relation_tf(self, rel):
        try:
            return round(Decimal(rel.frequency / rel.start_node.word_count[rel.type]), 6)
        except ZeroDivisionError:
            print("error calc tf:" + str(rel.start_node.lemmas) + " -> "+ str(rel.start_node.lemmas))
            return 0

    # сумма
    def calc_ngram_relation_weight_1(self, term_node, rel):
        s = 0
        # print(rel.end_node.lemmas)
        for unigram in NGramHelper.n_grams(list(rel.end_node.lemmas), 1):
            unigram_hash_set = Hasher.get_hash_set(unigram)
            unigram_hash = Hasher.hash(unigram_hash_set)
            if (len(term_node.hash_set) > 1) or (unigram_hash_set != term_node.hash_set):
                unigram_rel = term_node.get_out_relation_by_hash(unigram_hash, NodeRelationType.ASS)
                #if not (unigram_rel is None):
                s += unigram_rel.weight1
        rel.weight1 = s

    # вероятность
    def calc_ngram_relation_weight_2(self, term_node, rel):
        p = 1
        s = 0
        for unigram in NGramHelper.n_grams(list(rel.end_node.lemmas), 1):
            unigram_hash_set = Hasher.get_hash_set(unigram)
            unigram_hash = Hasher.hash(unigram_hash_set)
            if (len(term_node.hash_set) > 1) or (unigram_hash_set != term_node.hash_set):
                unigram_rel = term_node.get_out_relation_by_hash(unigram_hash, NodeRelationType.ASS)
                #if not (unigram_rel is None):
                p *= unigram_rel.tf
                s += unigram_rel.end_node.idf
        rel.weight2 = p * s

    # оценка по содержанию
    def calc_ngram_relation_weight_3(self, term_node, rel):
        s = 0
        for unigram in NGramHelper.n_grams(list(rel.end_node.lemmas), 1):
            unigram_hash_set = Hasher.get_hash_set(unigram)
            unigram_hash = Hasher.hash(unigram_hash_set)
            if (len(term_node.hash_set) > 1) or (unigram_hash_set != term_node.hash_set):
                unigram_rel = term_node.get_out_relation_by_hash(unigram_hash, NodeRelationType.ASS)
                #if not (unigram_rel is None):
                s += unigram_rel.tf_idf
        rel.weight3 = s * Decimal(log2(term_node.word_count[NodeRelationType.ASS]))

    def calc_tf_idf(self):
        for key, value in self.hash_terms.items():
            # учитывать только ассоциации
            for hash_end_node, rel in value.out_relations[NodeRelationType.ASS].items():
                if len(rel.end_node.hash_set) == 1:
                    rel.tf = self.get_relation_tf(rel)
                    if rel.end_node.idf is None:
                        rel.end_node.idf = self.get_node_idf(rel.end_node)
                    rel.tf_idf = round(rel.tf * rel.end_node.idf, 6)

    def calc_relation_weights(self):
        max_weight1 = max_weight2 = max_weight3 = Decimal(-1)
        for key, value in self.hash_terms.items():
            # часть целое
            # print(value.lemmas)
            for hash_end_node, rel in value.out_relations[NodeRelationType.GEN].items():
                rel.weight1 = rel.weight2 = rel.weight3 = \
                    round(Decimal(1 / (len(value.hash_set)) * len(rel.end_node.hash_set)), 6)
                max_weight1 = max(max_weight1, rel.weight1)
                max_weight2 = max(max_weight2, rel.weight2)
                max_weight3 = max(max_weight3, rel.weight3)

            # определение
            for hash_end_node, rel in value.out_relations[NodeRelationType.DEF].items():
                rel.weight1 = rel.weight2 = rel.weight3 = \
                    round(Decimal(1 / (value.word_count[NodeRelationType.DEF]) * len(rel.end_node.hash_set)), 6)
                max_weight1 = max(max_weight1, rel.weight1)
                max_weight2 = max(max_weight2, rel.weight2)
                max_weight3 = max(max_weight3, rel.weight3)

            # ассоциации
            for hash_end_node, rel in value.out_relations[NodeRelationType.ASS].items():
                if len(rel.end_node.hash_set) == 1:
                    rel.weight1 = rel.weight2 = rel.weight3 = rel.tf_idf
                else:
                    self.calc_ngram_relation_weight_1(value, rel)
                    self.calc_ngram_relation_weight_2(value, rel)
                    self.calc_ngram_relation_weight_3(value, rel)
                max_weight1 = max(max_weight1, rel.weight1)
                max_weight2 = max(max_weight2, rel.weight2)
                max_weight3 = max(max_weight3, rel.weight3)

        # нормализация ассоциаций
        for key, value in self.hash_terms.items():
            for hash_end_node, rel in value.out_relations[NodeRelationType.ASS].items():
                rel.weight1 = round(rel.weight1 / max_weight1, 6)
                rel.weight2 = round(rel.weight2 / max_weight2, 6)
                rel.weight3 = round(rel.weight3 / max_weight3, 6)
        print(max_weight1, max_weight2, max_weight3)

    def try_add_term(self, n_gram):
        lemmas = frozenset([t.lemma for t in n_gram])
        # в энциклопедии встречаются пустые термины
        if len(lemmas) == 0:
            return None
        h = Hasher.hash(Hasher.get_hash_set(lemmas))
        if h in self.hash_terms:
            term_node = self.hash_terms[h]
            if term_node.type == NodeType.CANDIDATE:
                term_node.type = NodeType.TERM
                self.term_count += 1
        else:
            term_node = Node(lemmas, NodeType.TERM)
            self.hash_terms[h] = term_node
            self.term_count += 1
        term_node.frequency += 1
        return term_node

    def try_add_candidate(self, term_node, n_gram, rel_type):
        lemmas = frozenset([t.lemma for t in n_gram])
        h = Hasher.hash(Hasher.get_hash_set(lemmas))
        # в статье о термине встретился этот термин
        if h == term_node.hash:
            return
        if h in self.hash_terms:
            node = self.hash_terms[h]
        else:
            # print(h, lemmas)
            node = Node(lemmas, NodeType.CANDIDATE)
            self.hash_terms[h] = node
        node.frequency += 1
        rel = term_node.get_out_relation(node, rel_type)
        if rel is None:
            term_node.add_out_relation(node, rel_type)
        else:
            rel.frequency += 1

    def get_node_neighborhood(self, node):
        neighbor_paths = []
        curr_path = NodePath()
        self.get_node_neighborhood_recur(node, neighbor_paths, curr_path)
        return neighbor_paths

    def get_node_neighborhood_recur(self, node, paths, curr_path):
        if curr_path.weight < MIN_PATH_WEIGHT:
            return
        if len(curr_path.relations) > 0:
            paths.append(curr_path)
        for rel_type in NodeRelationType:
            for node_hash in node.out_relations[rel_type]:
                new_path = NodePath()
                for rel in curr_path.relations:
                    new_path.relations.append(rel)
                rel = node.out_relations[rel_type][node_hash]
                new_path.weight = round(curr_path.weight * rel.weight1 * ATTENUATION, 6)
                new_path.relations.append(rel)
                self.get_node_neighborhood_recur(rel.end_node, paths, new_path)

    def get_max_path(self, start_node, end_node, curr_weight):
        if start_node.hash == end_node.hash:
            #print('ура ', curr_weight)
            return  curr_weight
        mx_weight = 0
        for rel_type in NodeRelationType:
            for node_hash in start_node.out_relations[rel_type]:
                rel = start_node.out_relations[rel_type][node_hash]
                if curr_weight * rel.weight1 > 0.001:
                    #print(rel.type, rel.start_node.lemmas, '=>',rel.end_node.lemmas, rel.weight1)
                    mx_weight = max(mx_weight, self.get_max_path(rel.end_node, end_node, curr_weight * rel.weight1))
        return mx_weight

    #вычисление интегральной характеристики узлов после отсечения
    def calc_node_weights(self, fname):
        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        for i in range(1, 501):
            cur.execute("INSERT INTO counter VALUES (" + str(i) + ")")

        for hash, node in self.hash_terms.items():
            count_rels = 0
            total_weights1 = total_weights2 = total_weights3 = 0
            for rel_type in NodeRelationType:
                for h, rel in node.out_relations[rel_type].items():
                    total_weights1 += rel.weight1
                    total_weights2 += rel.weight2
                    total_weights3 += rel.weight3
                    count_rels += 1
                for h, rel in node.in_relations[rel_type].items():
                    total_weights1 += rel.weight1
                    total_weights2 += rel.weight2
                    total_weights3 += rel.weight3
                    count_rels += 1
            v1 = round(Decimal(total_weights1/count_rels/Decimal(log2(count_rels + 1))), 6)
            v2 = round(Decimal(total_weights2/count_rels/Decimal(log2(count_rels + 1))), 6)
            v3 = round(Decimal(total_weights3/count_rels/Decimal(log2(count_rels + 1))), 6)
            print(node.lemmas, v1, v2, v3)
            cur.execute("update nodes set v1 = ?, v2 = ?,v3 = ?, count_rels = ? where hash = ?",
                        (str(v1), str(v2),str(v3), count_rels, str(hash)))
        conn.commit()
        cur.close()


