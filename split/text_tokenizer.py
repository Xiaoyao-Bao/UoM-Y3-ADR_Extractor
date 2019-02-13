import re

from nltk.tokenize import sent_tokenize
from nltk.tokenize import word_tokenize

files = open('/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_file_name.txt', "r").read().split('\n')
for filename in files:
    f = open('/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec/'+filename).read()
    new_name = "/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_token/" + filename
    sentences = sent_tokenize(f)
    with open(new_name, 'a') as n:
        for s in sentences:
            words = s.split()
            for w in words:
                if '≠' in w:
                    new = w.replace('≠',' ')
                    n.write("%s\n" % new)
                else:
                    for t in word_tokenize(w):
                        n.write("%s O\n" % t)
            n.write('\n')
    # break