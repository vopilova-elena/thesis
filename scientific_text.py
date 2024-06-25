from math import ceil
from copy import deepcopy
from abc import abstractmethod
from decimal import Decimal

# графики
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline

from hasher import Hasher
from base_graph import BaseNodeType
from ngram_helper import NGramHelper, N_MAX

EVAPORATIVITY = 0.9
PHEROMONE_DOSE = 1
CONTEXT_SIZE = 20


class ScientificText(object):
    def __init__(self, graph, syntax_helper):
        self.graph = graph
        self.syntax_helper = syntax_helper
        self.doc = None
        self.terms = dict()
        self.clusters = dict()
        self.final_term_weights = dict()
        self.contexts = []

    @abstractmethod
    def load_text(self, fname):
        pass

    def load_context_terms(self, start_sent_idx, end_sent_idx, use_evaporativity=False):
        for i in range(start_sent_idx, min(end_sent_idx + 1, len(self.doc.sents))):
            sent = self.doc.sents[i]
            valid_tokens = self.syntax_helper.get_valid_tokens(sent.tokens)
            #print('Предложение', i, ':', sent.text)

            # испарение
            if use_evaporativity:
                for term_hash, term in self.terms.items():
                    term['weight'] *= Decimal(EVAPORATIVITY)

            for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                lemmas = frozenset([t.lemma for t in n_gram])
                h = Hasher.hash(Hasher.get_hash_set(lemmas))

                if h in self.graph.nodes:
                    if h in self.terms:
                        self.terms[h]['weight'] += PHEROMONE_DOSE
                        self.terms[h]['frequency'] += 1
                    else:
                        self.terms[h] = {'frequency': 1, 'weight': PHEROMONE_DOSE, 'neighbours': dict()}
                        neighbors = self.graph.get_node_neighborhood(h)
                        for path in neighbors:
                            # каждый путь состоит из последовательных связей до конечного узла
                            # последняя связь содержит конечный вес всего пути
                            nbr_hash = path['edges'][-1][1]
                            if nbr_hash not in self.terms[h]['neighbours']:
                                self.terms[h]['neighbours'][nbr_hash] = 0
                            self.terms[h]['neighbours'][nbr_hash] = max(self.terms[h]['neighbours'][nbr_hash],
                                                                        path['weight'])

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

    # вывод терминов статьи и их соседей
    def print_terms_and_neighbours(self, extended=False):
        print('ТЕРМИНЫ ТЕКСТА')
        for term_hash, term in self.terms.items():
            print('ТЕРМИН', *self.graph.nodes[term_hash]['lemmas'], term['weight'], len(term['neighbours']))
            if extended:
                for nbr_hash, nbr_edge_weight in term['neighbours'].items():
                    print(*self.graph.nodes[nbr_hash]['lemmas'], 'ВЕС СВЯЗИ:', nbr_edge_weight)


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

    def clustering(self):
        medoids = self.__init_medoids()
        max_cost = 0
        cost, self.clusters = self.__fill_clusters(medoids)
        last_medoids = medoids.copy()
        i = 1
        while abs(max_cost - cost) > 0.001:  # пока медоиды не стабилизируются:
            max_cost = cost
            for medoid, cluster in self.clusters.items():
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
                    new_cost, clusters = self.__fill_clusters(medoids)
                    if new_cost > cost:
                        last_medoids = medoids.copy()
                        cost = new_cost
                    medoids.remove(node)
                    medoids.append(medoid)
            cost, self.clusters = self.__fill_clusters(last_medoids)

        # удаляем кластер с NONE центром
        del self.clusters[None]

        # считаем вес кластеров
        for medoid, cluster in self.clusters.items():
            cluster['weight'] = sum([self.final_term_weights[node_hash] for node_hash in cluster['nodes'].keys()])

   # выделение первичных медоидов
    def __init_medoids(self):
        c = []
        for term in self.terms.keys():
            node = self.graph.nodes[term]
            if node['type'] == BaseNodeType.TERM:
                c.append((term, node['centrality']))
        # print("Количество терминов: ", len(self.terms))
        cnt = min(max(3, round(len(self.terms) * 0.01)), 10)
        # print("Количество кластеров: ", cnt)
        y = [c[0] for c in sorted(c, key=lambda x: x[1], reverse=True)]
        medoids = y[:min(cnt, len(y))]
        medoids.append(None)
        # for m in medoids:
        #    print(*self.graph.nodes[m]['lemmas'])
        # print("end init medoids")
        return medoids

    # поиск ближайшего медоида
    def __get_closest_medoid(self, node_hash, medoids):
        closest_medoid = None
        cost = 0
        for medoid in medoids:
            if medoid is None:
                continue
            if (medoid in self.terms) and (node_hash in self.terms[medoid]['neighbours']):
                if self.terms[medoid]['neighbours'][node_hash] > cost:
                    # средневзвешенное: вес дуги * вес термина в статье
                    cost = self.terms[medoid]['neighbours'][node_hash] * self.final_term_weights[node_hash]
                    closest_medoid = medoid
        return closest_medoid, cost

    # распределяем узлы по медоидам
    def __fill_clusters(self, medoids):
        clusters = dict()
        for m in medoids:
            clusters[m] = {'weight': 0, 'nodes': dict()}

        total_cost = 0
        for term in self.terms.keys():
            if term in medoids:  # это медоид
                continue
            else:
                closest_medoid, cost = self.__get_closest_medoid(term, medoids)
                # если не найден кластер - то закидываем в спецкластер
                if cost == 0:
                    clusters[None]['nodes'][term] = 0
                else:
                    if term not in clusters[closest_medoid]['nodes']:
                        clusters[closest_medoid]['nodes'][term] = self.terms[closest_medoid]['neighbours'][term]  # cost
                total_cost += cost
        return total_cost, clusters
    def get_contexts(self):
        self.contexts.clear()
        context_count = ceil(len(self.doc.sents) / CONTEXT_SIZE)

        p = ScientificText(self.graph, self.syntax_helper)
        p.doc = deepcopy(self.doc)

        for i in range(0, context_count):
            p.load_context_terms(i * CONTEXT_SIZE, (i + 1) * CONTEXT_SIZE - 1, True)
            context_clusters = dict()
            self.contexts.append([min((i + 1) * CONTEXT_SIZE, len(self.doc.sents)),
                                  context_clusters,
                                  deepcopy(p.final_term_weights)])
            for medoid, cluster in self.clusters.items():
                if medoid is None:
                    continue
                cluster_weight = 0
                for node in cluster['nodes'].keys():
                    if node in p.terms:
                        cluster_weight += p.final_term_weights[node]
                context_clusters[medoid] = cluster_weight

    def contexts_to_img(self, fname):
        plt.clf()
        x = [0] + [context[0] for context in self.contexts]
        x_= np.linspace(min(x), max(x), num=10001, endpoint=True)

        for medoid in self.clusters.keys():
            y = [0]
            for context in self.contexts:
                y.append(context[1][medoid])
            spl = UnivariateSpline(x, y)
            spl.set_smoothing_factor(0.5)
            plt.plot(x_, spl(x_), label=' '.join(list(self.graph.nodes[medoid]['lemmas'])))

        plt.xlabel('Номер предложения')
        plt.ylabel('Вес кластера')
        plt.legend(loc=5)
        plt.grid(True)
        plt.gcf().set_size_inches(10, 5)
        plt.savefig(fname, dpi=200)
