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
i = 0
domain_clusters = []
print('Число кластеров: ' + str(len(communities)))
for community in communities:
    # метку кластера ставим всем узлам, даже из del_nodes
    for n in community:
        G.nodes[nodes[n]]['cluster'] = i

    community_nodes = [nodes[n] for n in community if nodes[n] not in del_nodes]
    if len(community_nodes) == 0:
        continue

    # в качестве медоида не может быть узел из del_nodes
    medoid = community_nodes[0]
    medoid_weight = sum([G.edges[e]['weight'] for e in G.edges(medoid)])
    for node in community_nodes:
        node_weight = sum([G.edges[e]['weight'] for e in G.edges(node)])
        if node_weight > medoid_weight:
            medoid = node
            medoid_weight = node_weight
    domain_clusters.append({'medoid': medoid, 'nodes': community_nodes})

    i += 1

node_domain_clusters = nx.get_node_attributes(G, 'cluster')

#паспорта
G = BaseGraph()
G.load_from_db('_db\\g_norm_ASS_GEN_DEF.db')

syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
files = Path('_in\\passports\\').glob('*.pdf')
pass_domain_clusters = dict()
for fname in files:
    p = ScientificPassport(G, syntax_helper)
    p.load_text(fname)
    p.load_context_terms(0, len(p.doc.sents) - 1, False)
    pass_domain_clusters[p.code] = {'name': p.name, 'clusters': set()}
    for node in p.terms.keys():
        if (G.nodes[node]['type'] == BaseNodeType.TERM) and (node in node_domain_clusters) and (node not in del_nodes):
            pass_domain_clusters[p.code]['clusters'].add(node_domain_clusters[node])

print('Паспорта')
print('  №  ', end=' ')
for j in range(len(communities)):
    print(f"{j:2d}", end=' ')
print()
for key, value in pass_domain_clusters.items():
    print(key, end=' ')
    for j in range(len(communities)):
        if j in value['clusters']:
            print(' 1', end=' ')
        else:
            print(' 0', end=' ')
    print()

#статьи
#dir_in = "_in\\papers\\Mathematics-Mechanics-Physics\\"
#dir_out = "_out\\papers\\Mathematics-Mechanics-Physics\\"
dir_in = "_in\\papers\\Математический сборник\\"
dir_out = "_out\\papers\\Математический сборник\\"
for directory in [d for d in Path(dir_in).iterdir() if d.is_dir()]:
    print('--------------------------------------------------')
    print('ПАПКА', directory.stem)
    files = Path(directory).glob('*.pdf')
    for fname in files:
        print('--------------------------------------------------')
        print('ФАЙЛ', fname.name)
        print('--------------------------------------------------')
        dir_out_file = dir_out + directory.stem + '\\' + fname.stem + "\\"
        if not (Path(dir_out_file).exists()):
            Path(dir_out_file).mkdir(parents=True)
        log_fname = dir_out_file + fname.stem + "_loading.txt"
        p = ScientificPaper(G, syntax_helper)
        p.load_text(fname.absolute())
        p.load_context_terms(0, len(p.doc.sents) - 1, False)

        paper_term_frequency = {}
        for node in p.terms.keys():
            if (G.nodes[node]['type'] == BaseNodeType.TERM) and (node in node_domain_clusters)  and (node not in del_nodes):
                if node_domain_clusters[node] not in paper_term_frequency:
                    paper_term_frequency[node_domain_clusters[node]] = 0
                paper_term_frequency[node_domain_clusters[node]] += p.terms[node]['frequency']
        #print(sorted(paper_term_frequency.keys()))
        for key1, value1 in pass_domain_clusters.items():
            k_inc = 0
            c = []
            for key2, value2 in paper_term_frequency.items():
                if key2 in value1['clusters']:
                    k_inc += value2
                    c.append([key2, value2])
            c = sorted(c, key=lambda item: -item[1])

            k_inc /= sum(paper_term_frequency.values())
            print(key1, f"{value1['name']:70}", f"{k_inc:.2f}    ", [' '.join(G.nodes[domain_clusters[item[0]]['medoid']]['lemmas']) for item in c])


