import sys

from logger import Logger
from base_graph import BaseGraph
from syntax_helper import SyntaxHelper
from graph_creator import GraphCreator


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Входные параметры: <имя XML-файла энциклопедии> <имя выходного файла - MDB или XML>')
    else:
        g = BaseGraph()
        syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")
        g.load_from_db('_db\\semantic_graph_new_3.db', True)
        #print(Logger.get_current_time() + ": creating graph...")
        graph_creator = GraphCreator(g, syntax_helper)
        '''graph_creator.load(sys.argv[1])
        print("terms count:", g.number_of_nodes())
        print(Logger.get_current_time() + ": add GEN relations")
        graph_creator.add_gen_relations()
        g.save_to_db('_db\\semantic_graph_new.db', detailed=True)
        print(Logger.get_current_time() + ": calcing nodes idf...")
        graph_creator.calc_nodes_idf()
        print(Logger.get_current_time() + ": calcing edges tf-idf...")
        graph_creator.calc_edges_tf_idf()'''
        print(Logger.get_current_time() + ": calcing edges weights...")
        graph_creator.calc_edges_weights()
        if sys.argv[2].endswith('db'):
            print(Logger.get_current_time() + ": saving to db...")
            g.save_to_db(sys.argv[2], detailed=True)
        elif sys.argv[2].endswith('xml'):
            print(Logger.get_current_time() + ": saving to xml...")
            g.save_to_xml(sys.argv[2], detailed=True)
        '''print(Logger.get_current_time() + ": graph created")'''