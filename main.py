from math import log, log2, log10, pow
from term_graph import TermGraph
from graph_loader import GraphLoader
from paper_loader import PaperLoader
from syntax_helper import SyntaxHelper
from logger import Logger
from hasher import Hasher
from paper_comparer import PaperComparer
import sqlite
def create_graph():
    global term_graph
    term_graph = TermGraph()
    syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
    graph_loader = GraphLoader(term_graph, syntax_helper)
    print(Logger.get_current_time() + ": creating graph...")
    graph_loader.load_file("_in\\dict\\out_all.txt")
    print("terms count: " + str(len(term_graph.hash_terms)))
    # #
    print("add gen relations")
    term_graph.add_gen_relations()
    print("calc tf and idf")
    term_graph.calc_tf_idf()
    print("calc_relation_weights")
    term_graph.calc_relation_weights()
    # #
    print("saving...")
    term_graph.save_to_db("_db\\semantic_graph.db")
    print(Logger.get_current_time() + ": graph created")

def load_graph(fname):
    print(Logger.get_current_time() + ": load graph...")
    graph = TermGraph()
    graph.load_from_db(fname)
    print(len(graph.hash_terms), "terms")
    print(Logger.get_current_time() + ": graph loaded")
    return graph


def get_node(term_graph, syntax_helper, text):
    doc = syntax_helper.load_text(text)
    syntax_helper.lemmatize(doc.sents[0].tokens)
    lemmas = frozenset([t.lemma for t in doc.sents[0].tokens])
    h = Hasher.hash(Hasher.get_hash_set(lemmas))
    return term_graph.hash_terms[h]

def build_neighborhood(term_graph, syntax_helper, text):
    node = get_node(term_graph, syntax_helper, text)
    print(str(node))
    node_neighbors = term_graph.get_node_neighborhood(node)
    for path in node_neighbors:
          print(str(path))


def analyse_text(term_graph, syntax_helper, fname):
    paper_loader = PaperLoader(term_graph, syntax_helper)
    print(Logger.get_current_time() + ": load paper...")
    s = cut_fname(fname)
    paper_loader.load_file("_in\\papers\\" + fname, "_out\\logs\\log_neighbors_" + s + ".txt")
    print(Logger.get_current_time() + ": save paper neighbors...")
    paper_loader.save_to_file("_out\\neighbors\\neighbors_" + s + ".csv")
    print(Logger.get_current_time() + ": paper neighbors saved")
    return paper_loader

def compare_papers(term_graph, syntax_helper, fname1, fname2):
    paper_loader1 = PaperLoader(term_graph, syntax_helper)
    log_fname1 = "_out\\logs\\log_neighbors_" + cut_fname(fname1) + ".txt"
    paper_loader1.load_file("_in\\papers\\" + fname1, log_fname1)

    paper_loader2 = PaperLoader(term_graph, syntax_helper)
    log_fname2 = "_out\\logs\\log_neighbors_" + cut_fname(fname2) + ".txt"
    paper_loader2.load_file("_in\\papers\\" + fname2, log_fname2)

    paper_comparer = PaperComparer(paper_loader1, paper_loader2)
    paper_comparer.fraction_of_intersection()
    paper_comparer.cosine_similarity()
    paper_comparer.naive_bayes()

def cut_fname(fname):
    idx = fname.rfind(".")
    if idx >= 0:
        fname = fname[:idx]
    return fname

#create_graph()
dbname = "_db\\semantic_graph_cuted1.db"
term_graph = load_graph(dbname)
d = dict()
# for h in term_graph.hash_terms:
#     node = term_graph.hash_terms[h]
#     if len(node.lemmas) not in d:
#         d[len(node.lemmas)] = 0
#     d[len(node.lemmas)] += 1
# print(d)
syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
paper_loader = PaperLoader(term_graph, syntax_helper)
fname = "p_4.txt"
log_fname = "_out\\logs\\log_neighbors_" + cut_fname(fname) + ".txt"
paper_loader.load_file("_in\\papers\\" + fname, log_fname)
paper_loader.save_to_file("_out\\neighbors\\neighbors_" + cut_fname(fname) + ".csv")
print("clustering")
print(Logger.get_current_time() + ": start clustering...")
paper_loader.clustering()
print(Logger.get_current_time() + ": end clustering...")
print("print_clusters_weights")
paper_loader.print_clusters(True)

#paper_loader.save_clusters(dbname)
# print("1")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_2_1.txt", log_fname)
# paper_loader.calc_clusters_weights()
# print("2")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_2_2.txt", log_fname)
# paper_loader.calc_clusters_weights()
# print("3")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_2_3.txt", log_fname)
# paper_loader.calc_clusters_weights()
# print("4")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_2.txt", log_fname)
# paper_loader.calc_clusters_weights()
# print("5")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_1_5.txt", log_fname)
# paper_loader.calc_clusters_weights()
# print("6")
# paper_loader.load_file_with_evaporativity("_in\\papers\\p_1.txt", log_fname)
# paper_loader.calc_clusters_weights()





