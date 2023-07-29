from ngram_helper import NGramHelper, N_MAX
from node_relation import NodeRelationType
from decimal import Decimal
from hasher import Hasher
import sqlite3

EVAPORATIVITY = 0.9
PHEROMONE_DOSE = 1
class PaperTerm(object):
    def __init__(self):
        self.weight = 0
        self.neighbours = dict()

class PaperCluster(object):
    def __init__(self):
        self.weight = 0
        self.nodes = dict()
class PaperLoader(object):
    def __init__(self, graph, syntax_helper):
        self.graph = graph
        self.syntax_helper = syntax_helper
        #self.descriptors = dict()
        self.log = None
        self.paper_terms = dict()
        self.clusters = dict()

    def load_file(self, fname, log_fname, use_evaporativity = False):
        f = open(fname, encoding="utf-8")
        text = " ".join(f.readlines())
        doc = self.syntax_helper.load_text(text)
        f.close()

        self.log = open(log_fname, "w", encoding="utf-8")

        for i in range(len(doc.sents)):
            sent = doc.sents[i]
            self.log.write('ПРЕДЛОЖЕНИЕ №' + str(i) + '\n')
            self.log.write(sent.text + '\n')
            self.syntax_helper.lemmatize(sent.tokens)
            valid_tokens = self.syntax_helper.get_valid_tokens(sent.tokens)

            # испарение
            if use_evaporativity:
                for key1, value1 in self.paper_terms.items():
                    value1.weight = Decimal(value1.weight) * Decimal(EVAPORATIVITY)
                    for key2, value2 in value1.neighbours.items():
                        value1.neighbours[key2] = Decimal(value2) * Decimal(EVAPORATIVITY)

            for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                lemmas = frozenset([t.lemma for t in n_gram])
                #print (lemmas)
                h = Hasher.hash(Hasher.get_hash_set(lemmas))
                if h in self.graph.hash_terms:
                    node = self.graph.hash_terms[h]
                    neighbors = self.graph.get_node_neighborhood(node)
                    for path in neighbors:
                        # каждый путь состоит из последовательных связей до конечного узла
                        if h not in self.paper_terms:
                            self.paper_terms[h] = PaperTerm()
                            self.paper_terms[h].weight = 1
                        #последняя связь содержит конечный вес всего пути
                        nh = path.relations[-1].end_node.hash
                        if nh not in self.paper_terms[h].neighbours:
                            self.paper_terms[h].neighbours[nh] = 0
                        self.paper_terms[h].neighbours[nh] = max(self.paper_terms[h].neighbours[nh], path.weight)
        #вывод терминов статьи и их соседей
        # for key1, value1 in self.paper_terms.items():
        #     print("term", self.graph.hash_terms[key1], value1.weight, len(value1.neighbours))
        #     for key2, value2 in value1.neighbours.items():
        #         print(self.graph.hash_terms[key2], value2)
        self.log.close()

    def save_to_file(self, fname):
        cnt = 0
        f = open(fname, "w")
        for key1, value1 in self.paper_terms.items():
            node1 = self.graph.hash_terms[key1]
            cnt += 1 + len(value1.neighbours)
            for key2, value2 in value1.neighbours.items():
                node2 = self.graph.hash_terms[key2]
                f.write(str(node1.type) + ';' + ' '.join(list(node1.lemmas)) + ';' +
                    str(value1.weight) + ';' +
                    str(node2.type) + ';' + ' '.join(list(node2.lemmas)) + ';' +
                    str(value2).replace('.', ',') + ';' + '\n')
        f.close()
        print(cnt)

    def print_clusters(self, extended = False):
        for key1, value1 in self.clusters.items():
            if key1 is None:
                print("medoid NULL")
            else:
                print("medoid", self.graph.hash_terms[key1].lemmas, value1.weight)
            if extended:
                for key2, value2 in value1.nodes.items():
                    print(self.graph.hash_terms[key2].lemmas, value2)

    # выделение первичных медоидов
    def init_medoids(self):
        #print("start init medoids")
        c = []
        for key, value in self.paper_terms.items():
            node = self.graph.hash_terms[key]
            c.append((key, len(node.out_relations[NodeRelationType.ASS]) + len(
            node.out_relations[NodeRelationType.DEF]) + len(node.out_relations[NodeRelationType.GEN])))
        y = [c[0] for c in sorted(c, key=lambda x: x[1])]
        #for key, value in self.neighbors.items():
        #    c.append([key, value])
        #y = [c[0] for c in sorted(c, key=lambda x: x[1])]

        cnt = 10#round(len(c) * 0.25)
        #print(cnt)
        medoids = []
        for i in range(cnt):
            medoids.append(y[-i - 1])
            node = self.graph.hash_terms[y[-i - 1]]
            #print(node.lemmas)
        #print("end init medoids")
        return medoids

    # поиск ближайшего медоида
    def get_closest_medoid(self, node_hash, medoids):
        closest_medoid = None
        cost = 0
        for medoid_hash in medoids:
            if medoid_hash is None:
                continue
            if (medoid_hash in self.paper_terms) and (node_hash in self.paper_terms[medoid_hash].neighbours):
                if self.paper_terms[medoid_hash].neighbours[node_hash] > cost:
                    cost = self.paper_terms[medoid_hash].neighbours[node_hash]
                    closest_medoid = medoid_hash
            if (node_hash in self.paper_terms) and (medoid_hash in self.paper_terms[node_hash].neighbours):
                if self.paper_terms[node_hash].neighbours[medoid_hash] > cost:
                    cost = self.paper_terms[node_hash].neighbours[medoid_hash]
                    closest_medoid = medoid_hash
        return  closest_medoid, cost


    # распределяем узлы по медоидам
    def fill_clusters(self, medoids):
        clusters = dict()
        for m in medoids:
            clusters[m] = PaperCluster()
        clusters[None] = PaperCluster()
        clusters[None].weight = 0

        total_cost = 0
        for key1, value1 in self.paper_terms.items():
            if key1 in medoids: #это медоид
                continue
            else:
                closest_medoid, cost = self.get_closest_medoid(key1, medoids)
                #если не найден кластер - то закидываем в спецкластер
                if cost == 0:
                    clusters[None].nodes[key1] = 0
                else:
                    if key1 not in clusters[closest_medoid].nodes:
                        clusters[closest_medoid].nodes[key1] = cost
                        clusters[closest_medoid].weight += cost
                        total_cost += cost

            for key2, value2 in value1.neighbours.items():
                if key2 in medoids:  # это медоид
                    continue
                else:
                    closest_medoid, cost = self.get_closest_medoid(key2, medoids)
                    # если не найден кластер - то закидываем в спецкластер
                    if cost == 0:
                        clusters[None].nodes[key2] = 0
                    else:
                        if key2 not in clusters[closest_medoid].nodes:
                            clusters[closest_medoid].nodes[key2] = cost
                            clusters[closest_medoid].weight += cost
                            total_cost += cost
        return total_cost, clusters

    def clustering(self):
        medoids = self.init_medoids()
        max_cost, self.clusters = self.fill_clusters(medoids)
        cost = 0
        last_medoids = medoids.copy()

        while abs(cost - max_cost) > 0.001: #пока медоиды не стабилизируются:
            print(cost, max_cost)
            medoids = list(self.clusters.keys())
            for medoid, value in self.clusters.items():
                for node in value.nodes:
                    medoids.remove(medoid)
                    medoids.append(node)
                    new_cost, clusters = self.fill_clusters(medoids)
                    if new_cost > max_cost:
                        last_medoids = medoids.copy()
                        print(max_cost, new_cost)
                        max_cost = new_cost
                    medoids.remove(node)
                    medoids.append(medoid)
            cost = max_cost
            max_cost, self.clusters = self.fill_clusters(last_medoids)




##saving
    # def load_file(self, fname, log_fname):
    #     f = open(fname, encoding="utf-8")
    #     text = " ".join(f.readlines())
    #     doc = self.syntax_helper.load_text(text)
    #     f.close()
    #
    #     self.log = open(log_fname, "w", encoding="utf-8")
    #
    #     for i in range(len(doc.sents)):
    #         sent = doc.sents[i]
    #         syntax_tree = None
    #         self.log.write('ПРЕДЛОЖЕНИЕ №' + str(i) + '\n')
    #         self.log.write(sent.text + '\n')
    #         self.syntax_helper.lemmatize(sent.tokens)
    #         valid_tokens = self.syntax_helper.get_valid_tokens(sent.tokens)
    #
    #         for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
    #             lemmas = frozenset([t.lemma for t in n_gram])
    #             #print (lemmas)
    #             h = Hasher.hash(Hasher.get_hash_set(lemmas))
    #             if h in self.graph.hash_terms:
    #                 node = self.graph.hash_terms[h]
    #                 if h in self.neighbors:
    #                     f = self.neighbors[h]
    #                     self.neighbors[h] = f + 1
    #                 else:
    #                     self.neighbors[h] = 1
    #                 self.log.write("Термин " + str(node.lemmas) + " " + str(self.neighbors[h]) + "\n")
    #                 node_neighbors = self.graph.get_node_neighborhood(node)
    #                 #self.log.write("ОКРЕСТНОСТЬ ТЕРМИНА " + str(node) + ': ' + str(len(node_neighbors)) + '\n')
    #                 #print("ОКРЕСТНОСТЬ ТЕРМИНА " + str(node) + ': ' + str(len(node_neighbors)))
    #                 for path in node_neighbors:
    #                     neighbour_hash = path.relations[-1].end_node.hash
    #                     neighbour_node = self.graph.hash_terms[neighbour_hash]
    #                     if neighbour_hash in self.neighbors:
    #                         f = self.neighbors[neighbour_hash]
    #                         self.neighbors[neighbour_hash] = f + path.weight
    #                     else:
    #                         self.neighbors[neighbour_hash] = path.weight
    #                     self.log.write("Термин окрестности " + str(neighbour_node.lemmas) + " " + str(self.neighbors[neighbour_hash])+ " " + str(path.weight) + "\n")
    #
    #     self.log.close()
    #     #deleting = []
    #     #for key, value in self.neighbors.items():
    #     #    node = self.graph.hash_terms[key]
    #     #    master_hash_node, w, v, step = value
    #     #    ww = Decimal(w) * Decimal(v)
    #     #    if master_hash_node is not None:
    #     #        _, master_w, master_v, master_step = self.neighbors[master_hash_node]
    #     #        self.neighbors[key] = (master_hash_node, w, master_v, master_step)
    #     #        ww = Decimal(w) * Decimal(master_v)
    #     #    if ww < Decimal(0.001):
    #     #        deleting.append(key)
    #
    #     #for key in deleting:
    #     #    self.neighbors.pop(key)
    #
    # #вывод дескрипторов
    #     # print("term descriptors")
    #     # for key in self.descriptors:
    #     #     dl = self.descriptors[key]
    #     #     print("Термин:" + str(list(self.graph.hash_terms[dl.hash_term].lemmas)))
    #     #     for i in range(len(dl.sents)):
    #     #         print(dl.sents[i].sent_idx + 1, ": internal", dl.sents[i].internal_rels, ", in", dl.sents[i].in_rels, ", out", dl.sents[i].out_rels)
    #

    # def try_add_to_neighbors(self, master_hash_node, hash_node, node_weight1, node_weight2, node_step):
    #     node = self.graph.hash_terms[hash_node]
    #     self.log.write("ТЕРМИН ОКРЕСТНОСТИ: " + str(node) + ', w=' + str(node_weight1) + '\n')
    #     if  hash_node in self.neighbors:
    #         mhn, w, v, step = self.neighbors[hash_node]
    #         self.log.write('УЖЕ ЕСТЬ В ОКРЕСТНОСТИ ТЕКСТА: ' + str(node) +
    #                 ', w= ' + str(w) +
    #                 ', v=' + str(v) +
    #                 ', шаг=' + str(step) + '\n')
    #         if w < node_weight1:
    #             w, v, step = node_weight1, v + node_weight2, node_step
    #             self.neighbors[hash_node] = (master_hash_node, w, v, step)
    #         else:
    #             w, v, step = w, v + node_weight2, node_step
    #             self.neighbors[hash_node] = (mhn, w, v, step)
    #         self.log.write('ЗАМЕНЕН В ОКРЕСТНОСТИ ТЕКСТА: ' + str(node) +
    #                 ', w= ' + str(w) +
    #                 ', v=' + str(v) +
    #                 ', шаг=' + str(step) + '\n')
    #     else:
    #         self.neighbors[hash_node] = (master_hash_node, node_weight1, node_weight2, node_step)
    #         self.log.write('ДОБАВЛЕН В ОКРЕСТНОСТЬ ТЕКСТА: ' + str(node) +
    #                 ', w= ' + str(node_weight1) +
    #                 ', v=' + str(PHEROMONE_DOSE) +
    #                 ', шаг=' + str(node_step) + '\n')
