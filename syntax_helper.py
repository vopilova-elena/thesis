from natasha import (Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger, PER,
                     NamesExtractor, Doc)
from hasher import Hasher
N_MAX = 3


class SyntaxHelper(object):
    def __init__(self, invalid_fname):
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
        self.syntax_parser = NewsSyntaxParser(self.emb)
        self.ner_tagger = NewsNERTagger(self.emb)
        self.fname = invalid_fname

    def lemmatize(self, tokens):
        for t in tokens:
            t.lemmatize(self.morph_vocab)

    @staticmethod
    def get_valid_tokens(tokens):
        res = []
        for t in tokens:
            if t.pos in [
                'NOUN'  # существительное
                , 'ADJ'  # прилагательное
                , 'PROPN'  # имя собственное
                , 'VERB'  # глагол
            ]:
                res.append(t)
        return res

    def has_valid_syntax_tree(self, tokens):
        if len(tokens) == 1:  # униграмма всегда синтаксически верна
            return True
        text = " ".join([t.text for t in tokens])
        syntax_tree = self.get_syntax_tree(text)
        rels = [t.rel for t in syntax_tree.tokens]
        if rels.count("root") <= 1:
            return True
        else:
            f = open(self.fname, "a")
            f.write(text + "\n")
            f.close()
            return False


    def get_syntax_tree(self, text):
        doc = self.load_text(text)
        doc.parse_syntax(self.syntax_parser)
        return doc.sents[0].syntax

    def get_syntax_tokens(self, sent, syntax_tree, tokens):
        r = []
        i = idx = 0
        t = list(tokens)
        j = 0
        h1 = Hasher.get_hash_set([t.lemma for t in tokens])
        for i in range(len(sent.tokens)):
            if i + len(tokens) >= len(sent.tokens):
                break
            h2 = Hasher.get_hash_set(t.lemma for t in sent.tokens[i: i + len(tokens)])
            if h1 == h2:
                for j in range(len(tokens)):
                    r.append(syntax_tree.tokens[i+j])
                break
        return r

    def load_text(self, text):
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        return doc
