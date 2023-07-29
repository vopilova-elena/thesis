class TermDescriptorList(object):
    def __init__(self, hash_term):
        self.hash_term = hash_term
        self.sents = []

    def add_sent(self, sent_idx, syntax_tree, syntax_tokens):
        self.sents.append(TermDescriptor(sent_idx, syntax_tree, syntax_tokens))


class TermDescriptor(object):
    def __init__(self, sent_idx, syntax_tree, syntax_tokens):
        self.sent_idx = sent_idx
        self.in_rels = dict()
        self.out_rels = dict()
        self.internal_rels = dict()
        syntax_token_ids = [t.id for t in syntax_tokens]
        for t in syntax_tree.tokens:
            if t.id in syntax_token_ids: # исходящие связи
                if t.head_id in syntax_token_ids: # внутренние связи
                    if t.rel not in self.internal_rels:
                        self.internal_rels[t.rel] = 0
                    self.internal_rels[t.rel] += 1
                else:
                    if t.rel not in self.in_rels:
                        self.in_rels[t.rel] = 0
                    self.in_rels[t.rel] += 1
            elif t.head_id in syntax_token_ids: #входящие связи
                    if t.rel not in self.out_rels:
                        self.out_rels[t.rel] = 0
                    self.out_rels[t.rel] += 1



