from syntax_helper import SyntaxHelper
from node_relation import NodeRelationType
from ngram_helper import NGramHelper, N_MAX
import re

class GraphLoader(object):
    def __init__(self, graph, syntax_helper):
        self.graph = graph
        self.syntax_helper = syntax_helper

    def papers(self, text):
        for p in re.finditer(r'<paper>'
                         r'<paperName>'
                         r'<name>'
                         r'([\w\s]*)'
                         r'</name>'
                         r'<detail>'
                         r'([\w\s]*)'
                         r'</detail>'
                         r'</paperName>'
                         r'<paperDef>'
                         r'([\w\s]*)'
                         r'</paperDef>'
                         r'<content>'
                         r'([\w\s]*)'
                         r'</content>'
                         r'</paper>', text):
            yield p

    def load_file(self, fname):
        # файл для синтаксически неверных n-грамм
        f = open(self.syntax_helper.fname, "w")
        f.close()

        f = open(fname, "r")
        s = f.read()
        s = s.replace('\n', '')
        for m in self.papers(s):
            text = m.group(1).lower()
            doc = self.syntax_helper.load_text(text)
            # термин
            for sent in doc.sents:
                print(sent.text)
                self.syntax_helper.lemmatize(sent.tokens)
                term_node = self.graph.try_add_term(sent.tokens)
            if term_node is None:
                continue

            # определение термина
            text = m.group(3).lower()
            doc = self.syntax_helper.load_text(text)
            for sent in doc.sents:
                self.syntax_helper.lemmatize(sent.tokens)
                valid_tokens = SyntaxHelper.get_valid_tokens(sent.tokens)
                term_node.word_count[NodeRelationType.DEF] += len(valid_tokens)
                for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                    if self.syntax_helper.has_valid_syntax_tree(n_gram):
                       self.graph.try_add_candidate(term_node, n_gram, NodeRelationType.DEF)
            #
            # статья о термине
            text = m.group(4).lower()
            doc = self.syntax_helper.load_text(text)
            for sent in doc.sents:
                self.syntax_helper.lemmatize(sent.tokens)
                valid_tokens = SyntaxHelper.get_valid_tokens(sent.tokens)
                term_node.word_count[NodeRelationType.ASS] += len(valid_tokens)
                for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                    if self.syntax_helper.has_valid_syntax_tree(n_gram):
                        self.graph.try_add_candidate(term_node, n_gram, NodeRelationType.ASS)
        f.close()
