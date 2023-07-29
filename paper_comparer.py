from paper_loader import PaperLoader

class PaperComparer(object):

    def __init__(self, paper_loader1, paper_loader2):
        self.paper_loader1 = paper_loader1
        self.paper_loader2 = paper_loader2

        self.paper_loader1.calc_path_weights()
        self.paper_loader1.clustering()

    #доля пересечения
    def fraction_of_intersection(self):
        s_w1 = s1_w1 = s_w2 = s1_w2 = 0
        for key, value in self.paper_loader1.neighbors.items():
            _1_w1, _1_w2, _ = value
            s1_w1 += _1_w1
            s1_w2 += _1_w2
            if key in self.paper_loader2.neighbors:
                _2_w1, _2_w2, _ = self.paper_loader2.neighbors[key]
                s_w1 += _1_w1
                s_w2 += _1_w2
        print("доля пересечения", s_w1 / s1_w1, s_w2 / s1_w2)

     #косинусное сходство
    def cosine_similarity(self):
        p_w1 = p_w2 = l1_w1 = l1_w2 = l2_w1 = l2_w2 = 0
        for key, value in self.paper_loader1.neighbors.items():
            _1_w1, _1_w2, _ = value
            l1_w1 += _1_w1 ** 2
            l1_w2 += _1_w2 ** 2
            if key in self.paper_loader2.neighbors:
                _2_w1, _2_w2, _ = self.paper_loader2.neighbors[key]
                p_w1 += _1_w1 * _2_w1
                p_w2 += _1_w2 * _2_w2
        l1_w1 = l1_w1 ** 0.5
        l1_w2 = l1_w2 ** 0.5
        for key, value in self.paper_loader2.neighbors.items():
            _2_w1, _2_w2, _ = value
            l2_w1 += _2_w1 ** 2
            l2_w2 += _2_w2 ** 2
        l2_w1 = l2_w1 ** 0.5
        l2_w2 = l2_w2 ** 0.5
        print("косинусное подобие", p_w1 / (l1_w1 * l2_w1), p_w2 / (l1_w2 * l2_w2))

    #наивный байес
    def naive_bayes(self):
        total_b = 0
        for medoid, nodes in self.paper_loader1.clusters.items():
            for key, value in self.paper_loader2.neighbors.items():
                if key == medoid or key in nodes:
                    total_b += 1
                    break
        print("наивный байес", total_b / len(self.paper_loader1.clusters))

    # веса кластеров
    def clusters_weights(self):
        total_wc = 0
        for medoid, nodes in self.paper_loader1.clusters.items():
            for key, value in self.paper_loader2.neighbors.items():
                if key == medoid or key in nodes:
                    total_wc += self.paper_loader1.cluster_weights[medoid]
                    break
        #
        #print("веса кластеров", total_wc / total_cluster_weights)







