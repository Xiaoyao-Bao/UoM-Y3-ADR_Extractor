import xml.etree.ElementTree as ET


f = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_file_name.txt", "r").read().split('\n')
for filename in f:
    abs_filename = '/Users/xyb/UoM-Y3-ADR_Extractor/split/dev/' + filename
    tree = ET.parse(abs_filename)
    root = tree.getroot()
    for child in root:
        # if child.tag == 'Text':
        #     for sec in child:
        #         sec_f = "/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec/" + filename[:-4] + sec.get('id') + ".txt"
        #         with open(sec_f, "w") as s:
        #             s.write(sec.text)
        if child.tag == 'Mentions':
            for mention in child:
                mention_f = "/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_label/" + filename[:-4] + mention.get('section') + ".txt"
                with open(mention_f, "a") as m:
                    m.write(mention.attrib.get('len') + ' ' + mention.attrib.get('start') + ' ' + mention.attrib.get('type') + '\n')
        # if child.tag == 'IgnoredRegions':
        #     for ig in child:
        #         ig_f = "/Users/xyb/UoM-Y3-ADR_Extractor/split/train_sec_label_ignore/" + filename[:-4] + ig.get('section') + ".txt"
        #         with open(ig_f, "a") as i:
        #             i.write(ig.attrib.get('len') + ' ' + ig.attrib.get('start') + '\n')
    # break
