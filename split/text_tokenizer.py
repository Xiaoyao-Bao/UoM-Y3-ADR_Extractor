from nltk.tokenize import sent_tokenize
from nltk.tokenize import word_tokenize

files = open('train_sec_file_name.txt', "r").read().split('\n')
for filename in files:
    f = open('/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec2/'+filename).read()
    new_name = "/Users/xyb/UoM-Y3-ADR_Extractor/split/train_token2/" + filename
    sentences = sent_tokenize(f)
    with open(new_name, 'a') as n:
        for s in sentences:
            words = word_tokenize(s)
            for w in words:
                n.write("%s\n" % w)
            n.write('\n')
    break