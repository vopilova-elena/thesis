from flask import Flask, request, render_template, redirect, url_for
from decimal import Decimal
from syntax_helper import SyntaxHelper
from base_graph import BaseGraph
from hasher import Hasher
import os.path

work_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
graph = BaseGraph()
graph.load_from_db(os.path.join(work_dir, "_db\\semantic_graph_terms.db"))

syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

@app.route("/")
@app.route("/<term>", methods = ['GET','POST'])
def index(term = None,nodes = []):
    print("index: ", term)
    if term is None:
        return render_template('index.html')
    elif len(nodes) == 0:
        doc = syntax_helper.load_text(term)
        syntax_helper.lemmatize(doc.sents[0].tokens)
        term_tokens = syntax_helper.get_valid_term(doc.sents[0].tokens)
        h = Hasher.hash(Hasher.get_hash_set([token.lemma for token in term_tokens]))


        if h in graph:
            nodes = [(str(graph.nodes[nbr]['type']),
                       " ".join(graph.nodes[nbr]['lemmas']),
                       str(edge['type']), Decimal.normalize(edge['weight']),
                       int(graph.nodes[nbr]['type']))
                      for nbr, nbr_edges in graph[h].items()
                      for edge in nbr_edges.values()]

            nodes.sort(key=lambda x: (-x[4], -x[3], x[1]))

        return render_template('index.html', term=term, is_term=(h in graph),nodes=nodes)
    else:
        return render_template('index.html', term=term, is_term=True,nodes=nodes)

@app.route('/neighbours',methods = ['POST'])
def neighbours():
      text = request.form['term']
      print('neighbours:', text)
      return redirect(url_for('index',term = text))

if __name__ == "__main__":
    app.run(debug=True)
