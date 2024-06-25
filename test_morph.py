from natasha import (Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger, PER,
                     NamesExtractor, Doc)
from ipymarkup import show_span_ascii_markup, show_dep_ascii_markup

segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
ner_tagger = NewsNERTagger(emb)
syntax_parser = NewsSyntaxParser(emb)


text = 'тангенс котангенс ареа'


doc = Doc(text)
doc.segment(segmenter)
doc.tag_morph(morph_tagger)
doc.parse_syntax(syntax_parser)

#print(doc.tokens)
for sent in doc.sents:
    for token in sent.tokens:
        token.lemmatize(morph_vocab)
        # if token.pos in [
        #     'NOUN'  # существительное
        #     , 'ADJ'  # прилагательное
        #     , 'PROPN'  # имя собственное
        #     , 'VERB'  # глагол
        # ]:
        print(token)
    for token in sent.syntax.tokens:
        print(token)
        sent.syntax



