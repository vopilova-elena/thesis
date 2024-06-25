import re
from math import ceil
from enum import IntEnum
from copy import deepcopy
from decimal import Decimal

#pymupdf library
import fitz

#графики
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline

from hasher import Hasher
from base_graph import BaseNodeType
from syntax_helper import SyntaxHelper
from ngram_helper import NGramHelper, N_MAX

EVAPORATIVITY = 0.9
PHEROMONE_DOSE = 1
PAPER_PART_SIZE = 20


class KeywordStatus(IntEnum):
    NONE = 0
    PART_OF_TERM = 1
    PART_OF_MEDOID = 2
    TERM = 3
    MEDOID = 4

class PaperKeyword(object):
    def __init__(self, hash_set, lemmas):
        self.hash_set = hash_set
        self.lemmas = lemmas
        self.count = 0
        self.status = KeywordStatus.NONE
        self.fraction_of_intersection = 0

class PaperLoader(object):
    def __init__(self, graph, syntax_helper):
        self.graph = graph
        self.syntax_helper = syntax_helper
        # self.descriptors = dict()
        self.log = None
        self.doc = None
        self.keywords = dict()
        self.terms = dict()
        self.clusters = dict()
        self.final_term_weights = dict()
        self.dynamics = []


    # выделение авторских ключевых слов
    def load_keywords(self):
        lines = re.search(r"Ключевые слова:([^\.]+)\.", self.doc.text).group(1).split('\n')
        #print(lines)
        #попытка убрать переносы
        for i in range(len(lines)):
            if len(lines[i])>0 and lines[i][-1] == "-":
                lines[i] = lines[i][:len(lines[i])-1]
        s = "".join(lines)
        s = s.replace("«", "").replace("»", "")

        keywords = re.findall(r"\w[^,;]+", s)
        for keyword in keywords:
            doc = self.syntax_helper.load_text(keyword)
            self.syntax_helper.lemmatize(doc.sents[0].tokens)
            lemmas = [t.lemma for t in doc.sents[0].tokens if t.pos not in ['ADP', 'CONJ', 'CCONJ']]
            hash_set = Hasher.get_hash_set(lemmas)
            h = Hasher.hash(hash_set)
            self.keywords[h] = PaperKeyword(hash_set, lemmas)


    def load_terms(self, log_fname, start_sent_idx, end_sent_idx, use_evaporativity=False):
        self.log = open(log_fname, "w", encoding="utf-8")
        for i in range(start_sent_idx, min(end_sent_idx + 1, len(self.doc.sents))):
            sent = self.doc.sents[i]
            self.log.write('ПРЕДЛОЖЕНИЕ №' + str(i) + '\n')
            self.log.write(sent.text + '\n')
            valid_tokens = self.syntax_helper.get_valid_tokens(sent.tokens)

            # испарение
            if use_evaporativity:
                for term_hash, term in self.terms.items():
                    term['weight'] *= Decimal(EVAPORATIVITY)

            for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                lemmas = frozenset([t.lemma for t in n_gram])
                h = Hasher.hash(Hasher.get_hash_set(lemmas))

                # проверка совпадения с ключевым словом
                # надо вычислять независимо от веса термина так как может использоваться испарение
                if h in self.keywords:
                    self.keywords[h].count += 1

                if h in self.graph.nodes:
                    if h in self.terms:
                        self.terms[h]['weight'] += PHEROMONE_DOSE
                    else:
                        self.terms[h] = {'weight': PHEROMONE_DOSE, 'neighbours': dict()}
                        neighbors = self.graph.get_node_neighborhood(h)
                        for path in neighbors:
                            # каждый путь состоит из последовательных связей до конечного узла
                            # последняя связь содержит конечный вес всего пути
                            nbr_hash = path['edges'][-1][1]
                            if nbr_hash not in self.terms[h]['neighbours']:
                                self.terms[h]['neighbours'][nbr_hash] = 0
                            self.terms[h]['neighbours'][nbr_hash] = max(self.terms[h]['neighbours'][nbr_hash], path['weight'])


        # распространение веса вершины на область
        self.final_term_weights.clear()
        extra_weights = dict()
        for term_hash in self.terms.keys():
            extra_weights[term_hash] = 0
        for term_hash, term in self.terms.items():
            for nbr_hash, nbr_edge_weight in term['neighbours'].items():
                if nbr_hash in self.terms:
                    extra_weights[nbr_hash] += nbr_edge_weight * self.terms[term_hash]['weight']
        for term_hash, term in self.terms.items():
             self.final_term_weights[term_hash] = self.terms[term_hash]['weight'] + extra_weights[term_hash]

        self.log.close()

    # вывод терминов статьи и их соседей
    def print_terms_and_neighbours(self, extended=False):
        for term_hash, term in self.terms.items():
            print('ТЕРМИН', *self.graph.nodes[term_hash]['lemmas'], term['weight'], len(term['neighbours']))
            if extended:
                for nbr_hash, nbr_edge_weight in term['neighbours'].items():
                    print(*self.graph.nodes[nbr_hash]['lemmas'], 'ВЕС СВЯЗИ:',nbr_edge_weight)



    def get_dynamics(self, fname):
        self.dynamics.clear()

        paper_parts_count = ceil(len(self.doc.sents) / PAPER_PART_SIZE)
        #print("Количество предложений:", len(self.doc.sents))
        #print("Количество блоков:", paper_parts_count)

        p = PaperLoader(self.graph, self.syntax_helper)
        p.doc = deepcopy(self.doc)

        col_headers = ['', '0']
        x=[0]

        for i in range(0, paper_parts_count):
            col_headers.append(str(min((i+1) * PAPER_PART_SIZE, len(self.doc.sents))))
            #p.terms.clear()
            p.load_terms("_out\\" + str(i + 1) + ".txt", i * PAPER_PART_SIZE, (i+1) * PAPER_PART_SIZE - 1,True)
            part_clusters = dict()
            self.dynamics.append([min((i+1) * PAPER_PART_SIZE, len(self.doc.sents)), part_clusters, deepcopy(p.final_term_weights)])
            #print('Блок', min((i+1) * PAPER_PART_SIZE, len(self.doc.sents)))
            for medoid, cluster in self.clusters.items():
                if medoid is None:
                    continue
                cluster_weight = 0
                for node in cluster['nodes'].keys():
                    if node in p.terms:
                        cluster_weight += p.final_term_weights[node]

                part_clusters[medoid] = cluster_weight
        #x_= np.linspace(min(x), max(x), num=10001, endpoint=True)

        # f = open(fname, "w")
        # f.write(';'.join(col_headers) + '\n')
        # for key, value in d.items():
        #     y = [0] + value
        #     spl = UnivariateSpline(x, y)
        #     spl.set_smoothing_factor(0.5)
        #     plt.plot(x_, spl(x_), label=' '.join(list(self.graph.nodes[key]['lemmas'])))
        #
        #     vv = ";".join([str(v).replace('.', ',') for v in value])
        #     f.write(' '.join(list(self.graph.nodes[key]['lemmas'])) + ';0;' + vv + '\n')
        # f.close()

    def dynamic_to_img(self, fname):
        plt.clf()
        x = [0] + [part[0] for part in self.dynamics]
        x_= np.linspace(min(x), max(x), num=10001, endpoint=True)
        for medoid in self.clusters.keys():
            y = [0]
            for part in self.dynamics:
                y.append(part[1][medoid])
            spl = UnivariateSpline(x, y)
            spl.set_smoothing_factor(0.5)
            plt.plot(x_, spl(x_), label=' '.join(list(self.graph.nodes[medoid]['lemmas'])))
        #plt.title(fname.stem)
        plt.xlabel('Номер предложения')
        plt.ylabel('Вес кластера')
        plt.legend(loc=5)
        plt.grid(True)
        plt.gcf().set_size_inches(10, 5)
        plt.savefig(fname, dpi=200)
        #plt.show()


    def load_file(self, fname):
        doc = fitz.open(fname)
        text = "".join([page.get_text() for page in doc])
        #print(text)
        self.doc = self.syntax_helper.load_text(text)
        for sent in self.doc.sents:
            self.syntax_helper.lemmatize(sent.tokens)

    def save_to_file(self, fname):
        cnt = 0
        f = open(fname, "w")
        for key1, value1 in self.terms.items():
            node1 = self.graph.nodes[key1]
            cnt += 1 + len(value1['neighbours'])
            for key2, value2 in value1['neighbours'].items():
                node2 = self.graph.nodes[key2]
                f.write(str(node1['type']) + ';' + ' '.join(list(node1['lemmas'])) + ';' +
                        str(value1['weight']) + ';' +
                        str(node2['type']) + ';' + ' '.join(list(node2['lemmas'])) + ';' +
                        str(value2).replace('.', ',') + ';' + '\n')
        f.close()

    def print_clusters(self, extended=False):
        total_weight = 0
        for medoid_hash, cluster in self.clusters.items():
            if (medoid_hash is None):
                pass
            else:
                total_weight += cluster['weight']
                print('МЕДОИД:', *self.graph.nodes[medoid_hash]['lemmas'],
                      ', ВЕС КЛАСТЕРА:', cluster['weight'],
                      ', КОЛИЧЕСТВО ТЕРМИНОВ:', len(cluster['nodes']) + 1)
                if extended:
                    sorted_nodes = sorted(list(cluster['nodes'].keys()) + [medoid_hash],
                                          key=lambda x: self.terms[x]['weight'], reverse=True)
                    for node_hash in sorted_nodes:
                        print(*self.graph.nodes[node_hash]['lemmas'],
                              ', ВЕС =', self.final_term_weights[node_hash])
                    print()
        print('ОБЩИЙ ВЕС КЛАСТЕРОВ:', total_weight)

    # выделение первичных медоидов
    def init_medoids(self):
        #print("start init medoids")
        c = []
        for key, value in self.terms.items():
            node = self.graph.nodes[key]
            if node['type'] == BaseNodeType.TERM:
                c.append((key, node['centrality']))
        #print("Количество терминов: ", len(self.terms))
        cnt = min(max(3, round(len(self.terms) * 0.01)), 10)
        #print("Количество кластеров: ", cnt)
        y = [c[0] for c in sorted(c, key=lambda x: x[1], reverse=True)]
        medoids = y[:min(cnt, len(y))]
        medoids.append(None)
        #for m in medoids:
        #    print(*self.graph.nodes[m]['lemmas'])
        #print("end init medoids")
        return medoids

    # поиск ближайшего медоида
    def get_closest_medoid(self, node_hash, medoids):
        closest_medoid = None
        cost = 0
        for medoid_hash in medoids:
            if medoid_hash is None:
                continue
            if (medoid_hash in self.terms) and (node_hash in self.terms[medoid_hash]['neighbours']):
                 if self.terms[medoid_hash]['neighbours'][node_hash] > cost:
                    # средневзвешенное: вес дуги * вес термина в статье
                    cost = self.terms[medoid_hash]['neighbours'][node_hash] * self.final_term_weights[node_hash]
                    closest_medoid = medoid_hash
        return closest_medoid, cost

    # распределяем узлы по медоидам
    def fill_clusters(self, medoids):
        clusters = dict()
        for m in medoids:
            clusters[m] = {'weight': 0, 'nodes': dict(), 'has_keyword': False}

        total_cost = 0
        for term_hash, term in self.terms.items():
            if term_hash in medoids:  # это медоид
                continue
            else:
                closest_medoid, cost = self.get_closest_medoid(term_hash, medoids)
                # если не найден кластер - то закидываем в спецкластер
                if cost == 0:
                    clusters[None]['nodes'][term_hash] = 0
                else:
                    if term_hash not in clusters[closest_medoid]['nodes']:
                        clusters[closest_medoid]['nodes'][term_hash] = self.terms[closest_medoid]['neighbours'][term_hash]  # cost
                total_cost += cost
        return total_cost, clusters

    def clustering(self):
        medoids = self.init_medoids()
        max_cost = 0
        cost, self.clusters = self.fill_clusters(medoids)
        last_medoids = medoids.copy()
        i = 1
        while abs(max_cost - cost) > 0.001:  # пока медоиды не стабилизируются:
            # print(f'{Fore.yellow}{max_cost}, {cost}, {len(self.clusters[None].nodes)}')
            max_cost = cost
            for medoid, value in self.clusters.items():
                #print('итерация', i)
                medoids = list(self.clusters.keys())
                i += 1
                if medoid is None:
                    continue
                # for node in value.nodes:
                for node in self.terms.keys():
                    if node in medoids:
                        continue
                    medoids.remove(medoid)
                    medoids.append(node)
                    new_cost, clusters = self.fill_clusters(medoids)
                    if new_cost > cost:
                        last_medoids = medoids.copy()
                        cost = new_cost
                    medoids.remove(node)
                    medoids.append(medoid)
            cost, self.clusters = self.fill_clusters(last_medoids)

        # удаляем кластер с NONE центром
        del self.clusters[None]

        #считаем вес кластеров
        for medoid_hash, cluster in self.clusters.items():
            cluster['weight'] = sum([self.final_term_weights[node_hash] for node_hash in cluster['nodes'].keys()])

#syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
#paper_loader = PaperLoader(None, syntax_helper)
#paper_loader.load_file('_in\\papers\\Mathematics-Mechanics-Physics\\v14_n2\\11938-26927-1-SM.pdf')
#paper_loader.load_keywords()