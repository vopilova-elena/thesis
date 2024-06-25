import re
import pymupdf
from scientific_text import ScientificText


class ScientificPassport(ScientificText):
    def __init__(self, graph, syntax_helper):
        ScientificText.__init__(self, graph, syntax_helper)
        self.code = ''
        self.name = ''

    def load_text(self, fname):
        doc = pymupdf.open(fname)
        text = "".join([page.get_text() for page in doc])
        match = re.search(
            r'Шифр научной специальности:\s?\n(\d+\.\d+\.\d+)\.\s([\w\s\.\(\),:;-]+)Направления исследований:', text)
        self.code = match.group(1)
        self.name = match.group(2).strip().replace('\n', ' ').replace('  ', ' ')
        # print(name)
        text = re.search(r'Направления исследований:\s?\n([\d\w\s\.\(\),:;-]+)Смежные \n?специальности', text).group(1)
        # print(text)
        self.doc = self.syntax_helper.load_text(text)
        for sent in self.doc.sents:
            self.syntax_helper.lemmatize(sent.tokens)
