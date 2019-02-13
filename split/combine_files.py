files = open("/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_file_name.txt", "r").read().split('\n')

with open("dev_BIO.txt", "wb") as outfile:
    for f in files:
        with open('/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_token/'+f, "rb") as infile:
            outfile.write(infile.read())