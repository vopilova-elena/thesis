from pathlib import Path

from syntax_helper import SyntaxHelper
from base_graph import BaseGraph, BaseNodeType, BaseNodeRelationType
from scientific_passport import ScientificPassport

syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

G = BaseGraph()
G.load_from_db('_db\\semantic_graph.db')

files = Path('_in\\passports\\').glob('*.pdf')
for fname in files:
    print()
    print('--------------------------------------------------')
    print('ФАЙЛ', fname.name)
    print('--------------------------------------------------')
    p = ScientificPassport(G, syntax_helper)
    p.load_text(fname)
    p.load_context_terms(0, len(p.doc.sents) - 1)
    p.print_terms_and_neighbours()
    p.clustering()
    p.print_clusters(extended=True)
