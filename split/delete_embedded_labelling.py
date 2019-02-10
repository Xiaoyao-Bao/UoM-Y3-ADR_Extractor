# Remove the repetitive single labelling lines
# files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_file_name.txt", "r").read().split('\n')
# for f in files:
#     lines = [line.rstrip('\n') for line in open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_wtSinRepDel/" + f)]
#     pre_start = 0
#     cur_start = 0
#     result = []
#     for l in lines:
#         label = l.split(" ")
#         if ',' not in label[0] and ',' not in label[1]:
#             cur_start = label[1]
#             if pre_start == cur_start:
#                 result.append(l)
#                 print(result)
#             pre_start = label[1]
#     print(len(lines))
#     for line in result:
#         lines.remove(line)
#         print(len(lines))
#     with open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_wtSinRepDel/" + f, "w") as nt:
#         for l in lines:
#             nt.write(l+'\n')
#     break

files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_file_name.txt", "r").read().split('\n')
for f in files:
    print(f)
    lines = [line.rstrip('\n') for line in open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_wtRepDel/" + f)]
    pre_start = []
    cur_start = []
    result = []
    for l in lines:
        tmp = l.split(" ")
        label = tmp[1].split(',')
        cur_start = label
        for cur in cur_start:
            if cur in pre_start:
                result.append(l)
                # print(result)
                break # Ignore rest of labels in current line, and, retain the last line of labels
        pre_start = label

    # print(len(lines))
    for line in result:
        lines.remove(line)
        # print(len(lines))

    last_end = -1
    for l in lines:
        tmp = l.split(" ")
        length = tmp[0].split(',')
        label = tmp[1].split(',')
        cur_begin = int(label[0])
        if last_end >= cur_begin:
            print(str(last_end)+'>='+str(cur_begin)+'!!!!!!!!!! '+l)
        last_end = int(label[-1])+int(length[-1])
    # with open("/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_wtSinRepDel/" + f, "w") as nt:
    #     for l in lines:
    #         nt.write(l+'\n')
    # break