from math import log, log2, log10, pow
fname="p_1.txt"
idx = fname.rfind(".")
if idx>=0:
    fname = fname[:idx]
print(fname)
