from base_graph import *
from syntax_helper import SyntaxHelper
from graph_creator import GraphCreator

g = BaseGraph()
g.load_from_db('_db\\semantic_graph_new_3.db', detailed=True)
syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
graph_creator = GraphCreator(g, syntax_helper)
graph_creator.calc_edges_weights()
g.save_to_db('_db\\semantic_graph_new_3_2.db', detailed=False)
