files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_file_name.txt", "r").read().split('\n')
for f in files:
    print(f)
    lines = [line.rstrip('\n') for line in open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_label_wtRepDel/" + f)]
    pre_start = []
    cur_start = []
    result = []
    for l in lines:
        tmp = l.split(" ")
        label = tmp[1].split(',')
        cur_start = label
        for cur in cur_start:
            if cur in pre_start:
                print('found~ ' + l)
                result.append(l)
                # print(result)
                break # Ignore rest of labels in current line, and, retain the last line of labels
        pre_start = label

    print(len(lines))
    for line in result:
        lines.remove(line)
    print(len(lines))

    result.clear() # Reset to empty
    pre_length = []
    pre_start = []
    for l in lines:
        tmp = l.split(" ")
        length = tmp[0].split(',') # Length list
        start = tmp[1].split(',') # Starting label list
        zipped_pre = list(zip(pre_length, pre_start))
        zipped_cur = list(zip(length, start))
        # print(zipped_labels)
        for pair_pre in zipped_pre:
            for pair_cur in zipped_cur:
                # print(pair[1]+'~' +start[0]+'~'+str(int(pair[1])+ int(pair[0])))
                if int(pair_pre[1]) <= int(pair_cur[1]) <= int(pair_pre[1]) + int(pair_pre[0]) or int(pair_pre[1]) <= int(pair_cur[1]) + int(pair_cur[0]) <= int(pair_pre[1]) + int(pair_pre[0]):
                    print('found! ' + l)
                    result.append(l)
                    break
            else: # Execute only when if didn't capture
                continue
            break # Break twice to break thoroughly
        pre_length = length
        pre_start = start

    print(len(lines))
    for line in result:
        lines.remove(line)
    print(len(lines))

    with open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_label_wtRepDel/" + f, "w") as nt:
        for l in lines:
            nt.write(l+'\n')
    # break