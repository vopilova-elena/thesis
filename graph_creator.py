import re
from math import log2, log10
from decimal import Decimal

from syntax_helper import SyntaxHelper
from base_graph import BaseGraph, BaseNodeType, BaseNodeRelationType
from ngram_helper import NGramHelper, N_MAX
from hasher import Hasher


class GraphCreator(object):
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

    def load(self, fname):
        # файл для синтаксически неверных n-грамм
        f = open(self.syntax_helper.fname, "w")
        f.close()

        f = open(fname, "r")
        s = f.read()
        s = s.replace('\n', '')
        for m in self.papers(s):
            term = None
            text = m.group(1).lower()
            doc = self.syntax_helper.load_text(text)
            # термин
            for sent in doc.sents:
                print(sent.text)
                self.syntax_helper.lemmatize(sent.tokens)
                valid_tokens = SyntaxHelper.get_valid_term(sent.tokens)
                term = self.try_add_term(valid_tokens)
            if term is None:
                continue

            # определение термина
            text = m.group(3).lower()
            doc = self.syntax_helper.load_text(text)
            for sent in doc.sents:
                self.syntax_helper.lemmatize(sent.tokens)
                valid_tokens = SyntaxHelper.get_valid_tokens(sent.tokens)
                self.graph.nodes[term]['len_definition'] += len(valid_tokens)
                for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                    if self.syntax_helper.has_noun(n_gram) and self.syntax_helper.has_valid_syntax_tree(n_gram):
                        self.try_add_candidate(term, n_gram, BaseNodeRelationType.DEF)
            #
            # статья о термине
            text = m.group(4).lower()
            doc = self.syntax_helper.load_text(text)
            for sent in doc.sents:
                self.syntax_helper.lemmatize(sent.tokens)
                valid_tokens = SyntaxHelper.get_valid_tokens(sent.tokens)
                self.graph.nodes[term]['len_content'] += len(valid_tokens)
                for n_gram in NGramHelper.n_grams(valid_tokens, N_MAX):
                    #if self.syntax_helper.has_noun(n_gram) and self.syntax_helper.has_valid_syntax_tree(n_gram):
                    if self.syntax_helper.has_valid_syntax_tree(n_gram):
                        self.try_add_candidate(term, n_gram, BaseNodeRelationType.ASS)
        f.close()

    def try_add_term(self, n_gram):
        lemmas = frozenset(sorted([t.lemma for t in n_gram]))
        # в энциклопедии встречаются пустые термины
        if len(lemmas) == 0:
            return None

        h = Hasher.hash(Hasher.get_hash_set(lemmas))

        if h in self.graph:
            self.graph.nodes[h]['type'] = BaseNodeType.TERM
        else:
            self.graph.add_node(h,
                                hash_set=Hasher.get_hash_set(lemmas),
                                lemmas=lemmas,
                                type=BaseNodeType.TERM,
                                centrality=0,
                                len_definition=0,
                                len_content=0,
                                idf=0
                                )
        return h

    def try_add_candidate(self, paper_term, n_gram, rel_type):
        lemmas = frozenset(sorted([t.lemma for t in n_gram]))
        h = Hasher.hash(Hasher.get_hash_set(lemmas))
        # в статье о термине встретился этот термин
        if h == paper_term:
            return h
        if h not in self.graph:
            self.graph.add_node(h,
                                hash_set=Hasher.get_hash_set(lemmas),
                                lemmas=lemmas,
                                type=BaseNodeType.CANDIDATE,
                                centrality=0,
                                len_definition=0,
                                len_content=0,
                                idf=0
                                )
        edges = []
        # ищем связь определенного типа
        if h in self.graph[paper_term]:
            edges = [key for key, value in self.graph[paper_term][h].items() if value['type'] == rel_type]
        if len(edges) == 0:
            self.graph.add_edge(paper_term,
                                h,
                                type=rel_type,
                                weight=0,
                                frequency=1,
                                tf=0,
                                tf_idf=0)
        else:
            self.graph[paper_term][h][edges[0]]['frequency'] += 1

        return h

    def add_gen_relations(self):
        # родовидове связи устанавливаются только между базовыми терминами
        terms = [h for h in self.graph.nodes if self.graph.nodes[h]['type'] == BaseNodeType.TERM]
        for term in terms:
            term_lemmas = self.graph.nodes[term]['lemmas']
            for lemmas in NGramHelper.n_grams_lemmas(list(term_lemmas), len(term_lemmas) - 1):
                h = Hasher.hash(Hasher.get_hash_set(lemmas))
                if h in terms:
                    self.graph.add_edge(term,
                                        h,
                                        type=BaseNodeRelationType.GEN,
                                        weight=0,
                                        frequency=0,
                                        tf=0,
                                        tf_idf=0)
                    # print(*self.graph.nodes[term]['lemmas'], '->', *self.graph.nodes[h]['lemmas'])

    def calc_nodes_idf(self):
        # tf-idf рассчитывается только для ассоциаций
        cnt_terms = len([h for h in self.graph.nodes if self.graph.nodes[h]['type'] == BaseNodeType.TERM])
        for node in self.graph:
            self.graph.nodes[node]['idf'] = 0
            if len(self.graph.nodes[node]['lemmas']) > 1:
                continue
            # print(*self.graph.nodes[node]['lemmas'])
            cnt_in_edges = len(
                [v for u, v, d in self.graph.in_edges(node, data=True) if d['type'] == BaseNodeRelationType.ASS])
            # print(*self.graph.nodes[node]['lemmas'], cnt_in_edges)
            if cnt_in_edges > 0:
                self.graph.nodes[node]['idf'] = Decimal.normalize(round(Decimal(log10(cnt_terms / cnt_in_edges)), 6))
            # print('idf',*self.graph.nodes[node]['lemmas'], self.graph.nodes[node]['idf'])

    def calc_edges_tf_idf(self):
        # tf-idf рассчитывается только для ассоциаций
        edges = [e for e in self.graph.edges if self.graph.edges[e]['type'] == BaseNodeRelationType.ASS]
        for e in edges:
            if len(self.graph.nodes[e[1]]['lemmas']) > 1:
                continue
            self.graph.edges[e]['tf'] = Decimal.normalize(round(
                Decimal(self.graph.edges[e]['frequency'] / self.graph.nodes[e[0]]['len_content']), 6))
            self.graph.edges[e]['tf_idf'] = Decimal.normalize(round(
                self.graph.edges[e]['tf'] * self.graph.nodes[e[1]]['idf'], 6))

    def calc_edges_weights(self):
        terms = [h for h in self.graph.nodes if self.graph.nodes[h]['type'] == BaseNodeType.TERM]
        # часть целое (нормализация не нужна)
        for term in terms:
            len1 = len(self.graph.nodes[term]['lemmas'])
            out_edges = [(u, v, k) for u, v, k, d in self.graph.out_edges(term, keys=True, data=True)
                         if d['type'] == BaseNodeRelationType.GEN]
            for e in out_edges:
                len2 = len(self.graph.nodes[e[1]]['lemmas'])
                self.graph.edges[e]['weight'] = Decimal.normalize(round(Decimal(len2 / len1), 6))
                # print('GEN', *self.graph.nodes[node]['lemmas'], '->', *self.graph.nodes[e[1]]['lemmas'], self.graph.edges[e]['weight'])

        # определение (нормализация не нужна)
        for term in terms:
            len1 = self.graph.nodes[term]['len_definition']
            out_edges = [(u, v, k) for u, v, k, d in self.graph.out_edges(term, keys=True, data=True)
                         if d['type'] == BaseNodeRelationType.DEF]
            for e in out_edges:
                len2 = len(self.graph.nodes[e[1]]['lemmas'])
                self.graph.edges[e]['weight'] = Decimal.normalize(round(Decimal(len2 / len1), 6))
                # print('DEF', *self.graph.nodes[node]['lemmas'], '->', *self.graph.nodes[e[1]]['lemmas'], self.graph.edges[e]['weight'])

        # ассоциации
        max_weight = 0
        for term in terms:
            out_edges = [(u, v, k) for u, v, k, d in self.graph.out_edges(term, keys=True, data=True)
                         if d['type'] == BaseNodeRelationType.ASS]
            for e in out_edges:
                if len(self.graph.nodes[e[1]]['lemmas']) == 1:
                    self.graph.edges[e]['weight'] = self.graph.edges[e]['tf_idf']
                else:
                    w = 0
                    for unigram in self.graph.nodes[e[1]]['lemmas']:
                        h = Hasher.hash(Hasher.get_hash_set(frozenset([unigram])))
                        out_unigram_edge = [ou for ou in out_edges if ou[1] == h]
                        for ue in out_unigram_edge:
                            w += self.graph.edges[ue]['tf_idf']
                    self.graph.edges[e]['weight'] = w * Decimal(log2(self.graph.nodes[term]['len_content']))
                if self.graph.nodes[e[1]]['type'] == BaseNodeType.TERM:
                    max_weight = max(max_weight, self.graph.edges[e]['weight'])
        print(max_weight)
        #  нормализация ассоциаций
        #edges = [e for e in self.graph.edges if self.graph.edges[e]['type'] == BaseNodeRelationType.ASS]
        edges = [e for e in self.graph.edges]
        #edges = [e for e in self.graph.edges if self.graph.edges[e]['type'] in (BaseNodeRelationType.ASS, BaseNodeRelationType.GEN)]
        for e in edges:
            self.graph.edges[e]['weight'] = Decimal.normalize(round((self.graph.edges[e]['weight'] / max_weight), 6))
            # print('ASS', *self.graph.nodes[e[0]]['lemmas'], '->', *self.graph.nodes[e[1]]['lemmas'], self.graph.edges[e]['weight'])

