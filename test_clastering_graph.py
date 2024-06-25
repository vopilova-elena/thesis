from builtins import range

from term_subgraph import TermSubgraph
import leidenalg

import numpy as np
import igraph as ig
import networkx as nx
from base_graph import *
from syntax_helper import SyntaxHelper
from scientific_passport import ScientificPassport
from scientific_paper import ScientificPaper

G = TermSubgraph()
G.load_from_db('_db\\g_norm_ASS_GEN_DEF.db')

del_nodes = []
for node in G:
    if len([e for e in G.edges(node)]) >= 300:
        del_nodes.append(node)
# for node in del_nodes:
#     st.remove_node(node)

G_ig = ig.Graph.from_networkx(G)
communities = leidenalg.find_partition(G_ig, leidenalg.ModularityVertexPartition,
                                       weights='weight', seed=1, max_comm_size=250, n_iterations=-1)

nodes = np.asarray(G_ig.vs["_nx_name"])
f = open('_out//clusters//clusters_norm_ASS_GEN_DEF.txt', 'w')
i = 0
print('Число кластеров: ' + str(len(communities)))
f.write('Число кластеров: ' + str(len(communities)) + '\n')
for community in communities:
    # метку кластера ставим всем узлам, даже из del_nodes
    for n in community:
        G.nodes[nodes[n]]['cluster'] = i

    community_nodes = [[nodes[n],0] for n in community if nodes[n] not in del_nodes]
    if len(community_nodes) == 0:
        continue
    # в качестве медоида не может быть узел из del_nodes
    for i in range(len(community_nodes)):
        community_nodes[i][1] = sum([G.edges[e]['weight'] for e in G.edges(community_nodes[i][0])])
    community_nodes = sorted(community_nodes, key=lambda item: -item[1])

    f.write('--------------------- кластер ' + str(i) + ' \"' + ' '.join(G.nodes[community_nodes[0][0]]['lemmas']) + '\",' +
            ' число терминов: ' + str(len(community_nodes)) + '\n')

    for i in range(len(community_nodes)):
        f.write(' '.join(G.nodes[community_nodes[i][0]]['lemmas']) + ', ' + str (community_nodes[i][1]) +'\n')
    i += 1

f.write('---------------------------------------------\n')
f.write('NO CLUSTER, число терминов ' + str(len(del_nodes)) + '\n')
for node in del_nodes:
    f.write(' '.join(G.nodes[node]['lemmas']) + ' (связей: ' + str(len([e for e in G.edges(node)])) + ')\n')
f.close()

# оценка связности между кластерами
'''matrix = [[0] * len(communities) for _ in communities]
i = 0
cluster_edge_weights = [0] * len(communities)
for community in communities:
    community_nodes = [nodes[n] for n in community if nodes[n] not in del_nodes]
    #community_nodes = [nodes[n] for n in community]
    for node in community_nodes:
        for nbr, nbr_edge in G_term[node].items():
            if nbr in del_nodes:
               continue
            cluster_edge_weights[i] += nbr_edge['weight']
            if G_term.nodes[nbr]['cluster'] != i:
                matrix[i][G_term.nodes[nbr]['cluster']] += nbr_edge['weight']
    if cluster_edge_weights[i] > 0:
        for j in range(len(matrix[i])):
            matrix[i][j] /= cluster_edge_weights[i]
    i+=1
#вывод матрицы
print(' ' * 2, end=' ')
for i in range(len(matrix)):
    print(f"{i:10.0f}", end=' ')
print()
for i in range(len(matrix)):
    print(f"{i:2.0f}", end=' ')
    for cell in matrix[i]:
        print(f"{cell:10.6f}", end=' ')
    print()
'''
# соответствие тематических и терминологических кластеров
'''matrix = []
passport_clusters = []
syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

term_clusters = nx.get_node_attributes(G, 'cluster')

G = BaseGraph()
G.load_from_db('_db\\g_norm_ASS_GEN_DEF.db')
files = Path('_in\\passports\\').glob('*.pdf')
for fname in files:
    print()
    print('--------------------------------------------------')
    print('ФАЙЛ', fname.name)
    print('--------------------------------------------------')
    p = ScientificPassport(G, syntax_helper)
    p.load_text(fname)
    p.load_context_terms(0, len(p.doc.sents) - 1)
    p.clustering()
    # p.print_clusters(extended=True)
    for medoid, cluster in p.clusters.items():
        matrix.append([0] * len(communities))
        pass_cluster_nodes = [n for n in list(cluster['nodes'].keys()) + [medoid] if
                              G.nodes[n]['type'] == BaseNodeType.TERM]
        passport_clusters.append(pass_cluster_nodes)
        if len(pass_cluster_nodes) == 0:
            continue
        for node in pass_cluster_nodes:
            if node in term_clusters:
                matrix[-1][term_clusters[node]] += 1
            else:
                print(*G.nodes[node]['lemmas'], G.nodes[node]['type'])
        for j in range(len(communities)):
            matrix[-1][j] /= len(pass_cluster_nodes)

print(' №', end=' ')
for j in range(len(communities)):
    print(f"{j:10.0f}", end=' ')
print()

for i in range(len(matrix)):
    print(f"{i:2.0f}", end=' ')
    s = 0
    for j in range(len(communities)):
        print(f"{matrix[i][j]:10.6f}", end=' ')
        s += matrix[i][j]
    print(f"{s:10.6f}", end=' ')
    print()

print('Терминологические кластера без тематических: ', end='')
for j in range(len(communities)):
    sm = sum([matrix[i][j] for i in range(len(passport_clusters))])
    if sm == 0:
        print(j, end=' ')
print()
'''
# определение паспортов статей
'''dir_in = "_in\\papers\\Mathematics-Mechanics-Physics\\"
dir_out = "_out\\papers\\Mathematics-Mechanics-Physics\\"
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
        paper_loader.load_terms(log_fname, 0, len(paper_loader.doc.sents) - 1, False)
        paper_loader.clustering()
        # paper_loader.print_clusters(extended=True)

        paper_term_clusters = {i: 0 for i in range(len(communities))}
        for medoid, cluster in paper_loader.clusters.items():
            paper_cluster_nodes = list(cluster['nodes'].keys()) + [medoid]
            for node in paper_cluster_nodes:
                if node in term_clusters:
                    paper_term_clusters[term_clusters[node]] += 1
        for i in range(len(communities)):
            if paper_term_clusters[i] > 0:
                print(i, ':', paper_term_clusters[i])
    break'''

