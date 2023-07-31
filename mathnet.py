from syntax_helper import SyntaxHelper
from term_graph import TermGraph
from hasher import Hasher
from logger import Logger

db_name = "_db\\semantic_graph_cuted1.db"
print(Logger.get_current_time() + ": load graph...")
graph = TermGraph()
graph.load_from_db(db_name)
print(len(graph.hash_terms), "terms")
print(Logger.get_current_time() + ": graph loaded")

syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

while True:
    text = input("Введите термин: ")
    if text == "quit":
        break
    doc = syntax_helper.load_text(text)
    syntax_helper.lemmatize(doc.sents[0].tokens)
    lemmas = frozenset([t.lemma for t in doc.sents[0].tokens])
    h = Hasher.hash(Hasher.get_hash_set(lemmas))
    if h in graph.hash_terms:
        node = graph.hash_terms[h]
        neighbors = graph.get_node_neighborhood(node)
        for path in neighbors:
            print(path)
    else:
        print('Термин "' + text + '" не найден')


