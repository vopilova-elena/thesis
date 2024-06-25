import re
import pymupdf
from enum import IntEnum

from hasher import Hasher
from scientific_text import ScientificText

class KeywordStatus(IntEnum):
    NONE = 0
    PART_OF_TERM = 1
    PART_OF_MEDOID = 2
    TERM = 3
    MEDOID = 4


class ScientificPaper(ScientificText):
    def __init__(self, graph, syntax_helper):
        ScientificText.__init__(self, graph, syntax_helper)
        self.keywords = dict()

    def load_text(self, fname):
        doc = pymupdf.open(fname)
        #doc = fitz.open(fname)
        text = "".join([page.get_text() for page in doc])
        #print(text)
        self.doc = self.syntax_helper.load_text(text)
        for sent in self.doc.sents:
            self.syntax_helper.lemmatize(sent.tokens)

    # выделение авторских ключевых слов
    def load_keywords(self):
        lines = re.search(r"Ключевые слова:([^\.]+)\.", self.doc.text).group(1).split('\n')
        #попытка убрать переносы
        for i in range(len(lines)):
            if len(lines[i])>0 and lines[i][-1] == "-":
                lines[i] = lines[i][:len(lines[i])-1]
        s = "".join(lines)
        s = s.replace("«", "").replace("»", "")

        keywords = re.findall(r"\w[^,;]+", s)
        for keyword in keywords:
            doc = self.syntax_helper.load_text(keyword)
            self.syntax_helper.lemmatize(doc.sents[0].tokens)
            lemmas = [t.lemma for t in doc.sents[0].tokens if t.pos not in ['ADP', 'CONJ', 'CCONJ']]
            hash_set = Hasher.get_hash_set(lemmas)
            h = Hasher.hash(hash_set)
            self.keywords[h] = {'hash_set': hash_set, 'lemmas': lemmas, 'frequency': 1}

    #переделать - вынести из кластера данные о ключевых словах!!!
    def calc_keywords_status(self):
        for hash_keyword, keyword in self.keywords.items():
            for hash_medoid, cluster in self.clusters.items():
                if hash_medoid is None:
                    continue
                if hash_keyword == hash_medoid:
                    keyword.status = KeywordStatus.MEDOID
                    keyword.fraction_of_intersection = 1
                    cluster['has_keyword'] = True
                    break
                elif hash_keyword in cluster.nodes:
                    keyword.status = KeywordStatus.TERM
                    keyword.fraction_of_intersection = 1
                    cluster['has_keyword'] = True
                    break
                else:
                    len_intersection = len(self.graph.nodes[hash_medoid]['hash_set'] & keyword.hash_set)
                    if len_intersection/len(keyword.hash_set) > keyword.fraction_of_intersection:
                        keyword.status = KeywordStatus.PART_OF_MEDOID
                        keyword.fraction_of_intersection = len_intersection/len(keyword.hash_set)
                        cluster['has_keyword'] = True
                    else:
                        for hash_node in cluster.nodes:
                            len_intersection = len(self.graph.nodes[hash_node]['hash_set'] & keyword.hash_set)
                            if len_intersection/len(keyword.hash_set) > keyword.fraction_of_intersection:
                                keyword.status = KeywordStatus.PART_OF_TERM
                                keyword.fraction_of_intersection = len_intersection / len(keyword.hash_set)
                                cluster['has_keyword'] = True
                                break

            if keyword.status == 4:
                print(keyword.lemmas, keyword.count, "центр кластера")
            elif keyword.status == 3:
                print(keyword.lemmas, keyword.count, "термин кластера")
            elif keyword.status == 2:
                print(keyword.lemmas, keyword.count, "пересекается с центром кластера")
            elif keyword.status == 1:
                print(keyword.lemmas, keyword.count, "пересекается с термином кластера")
            else:
                print(keyword.lemmas, keyword.count, "не найден")
