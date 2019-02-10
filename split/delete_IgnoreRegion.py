files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_file_name.txt", "r").read().split('\n')
for f in files:
    ignore_file = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_ignore/" + f, "r").read().split('\n')
    text_file = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec/" + f, "r").read()
    text_list = list(text_file)
    offset = 0
    for l in ignore_file:
        label = l.split(" ")
        length = int(label[0])
        i = int(label[1]) - offset
        str_to_del = text_list[i:i+length]
        del str_to_del
        offset += length
        # print(''.join(str_to_del))
    break