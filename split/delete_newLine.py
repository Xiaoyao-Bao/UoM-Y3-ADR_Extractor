# Delete the trailing new line at the end of files
import os
from pathlib import Path

files = open('dev_sec_file_name.txt', "r").read().split('\n')
for fname in files:
    fpath = '/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec_label_wtRepDel/' + fname
    if Path(fpath).is_file():
        f = open(fpath).read()
        new_f = f.rstrip()
        os.remove(fpath)
        f_write = open(fpath, 'w')
        f_write.write(new_f)
    else:
        print('Path doesn\'t exist!')
    # break
