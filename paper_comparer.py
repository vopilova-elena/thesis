from paper_loader import PaperLoader
from decimal import Decimal


class PaperComparer(object):

    def __init__(self, paper_loader1, paper_loader2):
        self.paper_loader1 = paper_loader1
        self.paper_loader2 = paper_loader2

        self.paper_loader1.clustering()

    # доля пересечения терминов
    def terms_fraction_of_intersection(self):
        paper1_weight = paper2_weight = 0
        for key, value in self.paper_loader1.paper_terms.items():
            paper1_weight += value.weight
            if key in self.paper_loader2.paper_terms:
                paper2_weight += value.weight
        print("доля пересечения терминов", round(paper2_weight / paper1_weight, 2))

    # косинусное сходство терминов
    def terms_cosine_similarity(self):
        p = paper1_len = paper2_len = 0
        for key, value in self.paper_loader1.paper_terms.items():
            paper1_len += value.weight ** 2
            if key in self.paper_loader2.paper_terms:
                _2_w1 = self.paper_loader2.paper_terms[key].weight
                p += value.weight * self.paper_loader2.paper_terms[key].weight
        paper1_len = float(paper1_len) ** 0.5
        for key, value in self.paper_loader2.paper_terms.items():
            paper2_len += value.weight ** 2
        paper2_len = float(paper2_len) ** 0.5
        print("косинусное подобие терминов", round(p / Decimal(paper1_len * paper2_len), 2))

    # доля веса кластеров
    def clusters_weights(self):
        total_cluster = 0
        # добавляем к весу кластера 1 - вес медоида
        total_clusters = sum([value.weight + 1
                              if (key is not None) else 0 for key, value in self.paper_loader1.clusters.items()])

        for key1, value1 in self.paper_loader1.clusters.items():
            if key1 is None:
                continue
            tt = 0
            cur_cluster_weight = 0
            if key1 in self.paper_loader2.paper_terms:
                cur_cluster_weight += 1
            for key2, value2 in value1.nodes.items():
                if key2 in self.paper_loader2.paper_terms:
                    cur_cluster_weight += value2
            total_cluster += cur_cluster_weight
        print("вес кластеров", total_cluster / total_clusters)

    # наивный байес терминов
    def terms_naive_bayes(self):
        total_b = 0
        for key, value in self.paper_loader1.paper_terms.items():
            if key in self.paper_loader2.paper_terms:
                total_b += 1
        print("наивный байес терминов", round(total_b / len(self.paper_loader1.paper_terms), 2))

    # наивный байес кластеров
    def clusters_naive_bayes(self):
        total_b = 0
        for medoid, cluster in self.paper_loader1.clusters.items():
            if medoid in self.paper_loader2.paper_terms:
                total_b += 1
            else:
                for key in cluster.nodes:
                    if key in self.paper_loader2.paper_terms:
                        total_b += 1
                        break
        print("наивный байес кластеров", round(total_b / len(self.paper_loader1.clusters), 2))

# def compare_papers(term_graph, syntax_helper, fname1, fname2, use_evaporativity):
#     paper_loader1 = PaperLoader(term_graph, syntax_helper)
#     log_fname1 = "_out\\logs\\log_neighbors_" + cut_fname(fname1) + ".txt"
#     paper_loader1.load_file("_in\\papers\\" + fname1, log_fname1, use_evaporativity)
#
#     paper_loader2 = PaperLoader(term_graph, syntax_helper)
#     log_fname2 = "_out\\logs\\log_neighbors_" + cut_fname(fname2) + ".txt"
#     paper_loader2.load_file("_in\\papers\\" + fname2, log_fname2, use_evaporativity)
#
#     paper_comparer = PaperComparer(paper_loader1, paper_loader2)
#     paper_comparer.terms_fraction_of_intersection()
#     paper_comparer.terms_naive_bayes()
#     paper_comparer.clusters_naive_bayes()
#     paper_comparer.terms_cosine_similarity()
#     paper_comparer.clusters_weights()


# сравнение статей
# dbname = "_db\\semantic_graph_cuted1.db"
# term_graph = load_graph(dbname)
# syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
# fname1 = "p_1.txt"
# fname2 = "p_1_#.txt"
# print("без затухания")
# compare_papers(term_graph, syntax_helper, fname1, fname2, 0)
# print("с затуханием")
# compare_papers(term_graph, syntax_helper, fname1, fname2, 1)


