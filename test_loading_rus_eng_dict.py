import re
from base_graph import *
from syntax_helper import SyntaxHelper

g = BaseGraph()
g.load_from_db('_db\\g_norm_ASS.db', detailed=False)
syntax_helper = SyntaxHelper("_out\\invalid_ngrams.txt")

f = open('_in\\dict\\math_eng_dict.txt')
text = f.readlines()
i = 0
j = 0
k = 0
for line in text:
    #print(line)
    for p in re.finditer(r'([а-я()\s]+)'
                         r'\t+'
                         r'([a-zA-Z,\s]+)',line):
        i += 1
        rus_text = p.group(1)
        eng_text = p.group(2)
        doc = syntax_helper.load_text(rus_text)
        for sent in doc.sents:
            syntax_helper.lemmatize(sent.tokens)
            valid_tokens = SyntaxHelper.get_valid_term(sent.tokens)
            lemmas = frozenset(sorted([t.lemma for t in valid_tokens]))
            h = Hasher.hash(Hasher.get_hash_set(lemmas))
            if h in g:
                if g.nodes[h]['type'] == BaseNodeType.TERM:
                    j += 1
                else:
                    k += 1
                print(*lemmas, eng_text)
print(i, j, k)

