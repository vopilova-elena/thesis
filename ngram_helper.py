N_MAX = 3


class NGramHelper(object):
    @staticmethod
    def n_grams_lemmas(lemmas, max_N):
        for i in range(1, max_N + 1):
            for j in range(0, len(lemmas) - i + 1):
                r = []
                for k in range(i):
                    r.append(lemmas[j + k])
                yield r

    @staticmethod
    def n_grams(tokens, max_N):
        for i in range(1, max_N + 1):
            for j in range(0, len(tokens) - i + 1):
                yield [tokens[j + k] for k in range(i)]
