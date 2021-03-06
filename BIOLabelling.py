import re
from nltk.tokenize import word_tokenize


def my_tokenizer(x):
    new = []
    temp = []
    for l in x:
        if l.isalpha():
            temp.append(l)
        else:
            if temp: # If temp is not empty
                new.append(''.join(temp))
                temp.clear()
            new.append(l)
    if temp:
        new.append(''.join(temp))
        temp.clear()
    return new


files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_file_name.txt", "r").read().split('\n')
for f in files:
    print(f)
    label_file = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_label_wtRepDel/" + f, "r").read().split('\n')
    text_file = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec/" + f, "r").read()
    text_list = list(text_file)
    offset = 0
    for l in label_file:
        label = l.split(" ")
        if ',' not in label[0] and ',' not in label[1]:
            length = int(label[0])
            i = int(label[1])+offset
            tokens = ''.join(text_list[i:i + length]).split()
            count = 0
            for token in tokens:
                for t in my_tokenizer(list(token)):
                    # print(text_list[i:i + len(token)])
                    count += 1
                    if count == 1:#B
                        new_str = list(' ') + text_list[i:i + len(t)] + list('≠B-' + label[2] + ' ')
                    else:#I
                        new_str = list(' ') + text_list[i:i + len(t)] + list('≠I-' + label[2] + ' ')
                    # print(''.join(new_str))
                    text_list[i:i + len(t)] = new_str
                    offset += len(label[2])+5
                    i += len(new_str)
                    while text_list[i] == ' ':
                        i+=1
        else:
        # # if ',' in label[0] and ',' in label[1]:
            length_list = label[0].split(',')
            start_list = label[1].split(',')
            zipped_labels = list(zip(length_list, start_list))
            count = 0
            for pair in zipped_labels:
                # print(pair[0]+',,,'+pair[1])
                length = int(pair[0])
                i = int(pair[1]) + offset
                tokens = word_tokenize(''.join(text_list[i:i + length]))
                for token in tokens:
                    for t in my_tokenizer(list(token)): # Tokenise non_alpha char separately from words
                        # print(text_list[i:i + len(token)])
                        count += 1
                        if count == 1:#B
                            new_str = list(' ') + text_list[i:i + len(t)] + list('≠B-' + label[2] + ' ')
                        else:
                            new_str = list(' ') + text_list[i:i + len(t)] + list('≠I-' + label[2] + ' ')
                        # print(''.join(new_str))
                        text_list[i:i + len(t)] = new_str
                        offset += len(label[2]) + 5
                        i += len(new_str)
                        while text_list[i] == ' ':
                            i += 1
    new_text = ''.join(text_list)
    # print(new_text)
    with open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec/" + f, "w") as nt:
        nt.write(new_text)
    # break