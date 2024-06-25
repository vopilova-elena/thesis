import sys
from pathlib import Path

from base_graph import BaseGraph, BaseNodeType, BaseNodeRelationType
from paper_loader import PaperLoader, KeywordStatus
from syntax_helper import SyntaxHelper
from logger import Logger
from decimal import Decimal


def load_graph(fname):
    print(Logger.get_current_time() + ": load graph...")
    graph = BaseGraph()
    graph.load_from_db(fname)
    print(graph.number_of_nodes(), "terms,", graph.number_of_edges(), "edges")
    print(Logger.get_current_time() + ": graph loaded")
    return graph


G = load_graph("_db\\semantic_graph.db")
syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

total_count = dict()
total_fraction_of_intersection = dict()
total_len_count = dict()
total_len_status = dict()
for status in KeywordStatus:
    total_count[status] = 0
    total_fraction_of_intersection[status] = 0

dir_in = "_in\\papers\\Mathematics-Mechanics-Physics\\"
dir_out = "_out\\papers\\Mathematics-Mechanics-Physics\\"

count_new_terms = 0
count_candidates = 0
count_GEN = 0
count_ASS = 0

for directory in [d for d in Path(dir_in).iterdir() if d.is_dir()]:
    print('--------------------------------------------------')
    print('ПАПКА', directory.stem)
    files = Path(directory).glob('*.pdf')
    for fname in files:
        print('--------------------------------------------------')
        print('ФАЙЛ', fname.name)
        dir_out_file = dir_out + directory.stem + '\\' + fname.stem + "\\"
        if not (Path(dir_out_file).exists()):
            Path(dir_out_file).mkdir(parents=True)
        log_fname = dir_out_file + fname.stem + "_loading.txt"
        paper_loader = PaperLoader(G, syntax_helper)
        paper_loader.load_file(fname.absolute())
        paper_loader.load_keywords()
        paper_loader.load_terms(log_fname, 0, len(paper_loader.doc.sents) - 1, False)
        #paper_loader.save_to_file(dir_out_file + fname.stem + "_neighbors.csv")
        # paper_loader.print_terms_and_neighbours(True)

        #print(Logger.get_current_time() + ": start clustering...")
        paper_loader.clustering()
        #print(Logger.get_current_time() + ": end clustering...")

        print()
        print("КЛАСТЕРЫ")
        paper_loader.print_clusters(False)
        total_clusters_weight = sum([cluster['weight'] for cluster in paper_loader.clusters.values()])

        # print("ДИНАМИКА")
        paper_loader.get_dynamics(dir_out_file + fname.stem + "_dynamic.csv")
        #paper_loader.dynamic_to_img('_out\\img\\Математический сборник\\' + fname.stem + ".jpg")

        print()
        print("КЛЮЧЕВЫЕ СЛОВА")
        for hash_keyword, keyword in paper_loader.keywords.items():
            if (hash_keyword in G):
                if G.nodes[hash_keyword]['type'] == BaseNodeType.TERM:
                    print("KEYWORD (TERM):", *keyword.lemmas, "ЧАСТОТНОСТЬ:", keyword.count)
                else:
                    print("KEYWORD (CANDIDATE):", *keyword.lemmas, "ЧАСТОТНОСТЬ:", keyword.count)
                    count_candidates += 1
            else:
                print("KEYWORD (не найдено):", *keyword.lemmas, "ЧАСТОТНОСТЬ:", keyword.count)
                count_new_terms += 1

        print()
        print("НОВЫЕ СВЯЗИ: ЧАСТЬ-ЦЕЛОЕ (в обе стороны)")
        for hash_keyword, keyword in paper_loader.keywords.items():
            if (hash_keyword in G) and (G.nodes[hash_keyword]['type'] == BaseNodeType.TERM):
                continue
            # связи "часть-целое" с терминами
            for term in G:
                term_hash_set = G.nodes[term]['hash_set']
                if term_hash_set == keyword.hash_set:
                    continue
                intersection = term_hash_set.intersection(keyword.hash_set)
                if intersection == term_hash_set:
                    print('KEYWORD', *keyword.lemmas, "->", G.nodes[term]['type'], *G.nodes[term]['lemmas'],
                          'ТИП:', BaseNodeRelationType.GEN,
                          'ВЕС:', Decimal.normalize(round(Decimal(1 / (len(keyword.hash_set)) * len(term_hash_set)), 6)))
                    count_GEN += 1
                if intersection == keyword.hash_set:
                    print(G.nodes[term]['type'], *G.nodes[term]['lemmas'], "->", 'KEYWORD', *keyword.lemmas,
                          'ТИП:', BaseNodeRelationType.GEN,
                          "ВЕС:", Decimal.normalize(round(Decimal(1 / (len(term_hash_set)) * len(keyword.hash_set)), 6)))
                    count_GEN += 1
        print()
        # связи с центрами кластеров
        print("НОВЫЕ СВЯЗИ: АССОЦИАЦИИ (от ключевого слова к центру кластера)")
        for hash_keyword, keyword in paper_loader.keywords.items():
            for medoid_hash, cluster in paper_loader.clusters.items():
                print('KEYWORD', *keyword.lemmas, "->", G.nodes[medoid_hash]['type'], *G.nodes[medoid_hash]['lemmas'],
                      'ТИП:', BaseNodeRelationType.ASS,
                      "ВЕС:", Decimal.normalize(round(Decimal(cluster['weight'] / total_clusters_weight), 6)))
                count_ASS += 1

        # связи от центра кластеров к ключевому слову
        print()
        print("НОВЫЕ СВЯЗИ: АССОЦИАЦИИ (от центра кластера к ключевму слову)")
        kw = dict()
        for medoid in paper_loader.clusters.keys():
            kw[medoid] = dict()
            for hash_keyword, keyword in paper_loader.keywords.items():
                kw[medoid][hash_keyword] = 0
        for part in paper_loader.dynamics:  # по блокам текста
            #print('Блок', part[0])
            part_term_weights = part[2]  # веса терминов в блоке
            for medoid, cluster in paper_loader.clusters.items():
                if medoid not in part[1].keys():  # по кластерам блока
                    continue
                #print(*G.nodes[medoid]['lemmas'])
                #print(cluster)
                #print(part[2])
                for hash_keyword, keyword in paper_loader.keywords.items():
                    if (hash_keyword in cluster['nodes']) and (hash_keyword in part_term_weights):
                        #print(*keyword.lemmas, '?', *G.nodes[medoid]['lemmas'])
                        #print(part_term_weights[hash_keyword], paper_loader.final_term_weights[hash_keyword], \
                        #      part[1][medoid], cluster['weight'])
                        kw[medoid][hash_keyword] += \
                            part_term_weights[hash_keyword] / paper_loader.final_term_weights[hash_keyword] * \
                            part[1][medoid] / cluster['weight']
        for medoid in paper_loader.clusters.keys():
            for hash_keyword, keyword in paper_loader.keywords.items():
                if kw[medoid][hash_keyword]>0:
                    print(G.nodes[medoid]['type'], *G.nodes[medoid]['lemmas'], '->', 'KEYWORD', *keyword.lemmas,
                          'ТИП:', BaseNodeRelationType.ASS,
                          "ВЕС:", Decimal.normalize(round(Decimal(kw[medoid][hash_keyword]), 6)))

            count_ASS += 1
print('Число кандидатов:', count_candidates)
print('Число новых терминов:', count_new_terms)
print('GEN:', count_GEN)
print('ASS:', count_ASS)
#
#         paper_loader.calc_keywords_status()
#         for hash_keyword, keyword in paper_loader.keywords.items():
#             #total_count[keyword.status] += 1
#             #total_fraction_of_intersection[keyword.status] += keyword.fraction_of_intersection
#             #l = len(keyword.hash_set)
#             #if l not in total_len_count:
#             #    total_len_count[l] = []
#             #    total_len_status[l] = 0
#             #total_len_count[l].append(keyword.count)
#             #if keyword.count == 0:
#             #    print("0:",  keyword.lemmas, fname)
#             #if keyword.status != KeywordStatus.NONE:
#             #    total_len_status[l] += 1
#             l = len(keyword.hash_set)
#             if l not in cm:
#                 cm[l] = [0, 0, 0]
#             if keyword.status == KeywordStatus.NONE:
#                 cm[l][2] += 1
#             else:
#                 cm[l][0] += 1
#         for hash_medoid, cluster in paper_loader.clusters.items():
#             if hash_medoid is None:
#                 continue
#             l = len(g.nodes[hash_medoid]['hash_set'])
#             if l not in cm:
#                 cm[l] = [0, 0, 0]
#             if not cluster.has_keyword:
#                 cm[l][1] += 1
#
#
# print("Confusion Matrix")
# print("Len  TP FP FN")
# for key, value in cm.items():
#     print(key, value[0], value[1], value[2])
#
# print("Содержание в кластерах")
# for status in KeywordStatus:
#    print(status, total_count[status], total_fraction_of_intersection[status])
# print("Сколько раз встречается")
# for key, value in total_len_count.items():
#    print(key, len(value), min(value), max(value), total_len_status[key])

# paper_loader.save_to_file("_out\\logs\\" + fname.stem + ".csv")
#  paper_loader.get_dynamics("_out\\dynamic\\n3\\" + fname.stem + ".csv")
