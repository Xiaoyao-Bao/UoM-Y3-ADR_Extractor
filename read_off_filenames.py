import os

# Open a file
path = '/Users/xyb/UoM-Y3-ADR_Extractor/split/dev_sec'
name_list = os.listdir(path)

# This would write all the (sorted)files and directories into training_file_name.txt
name_list.sort()

with open('dev_sec_file_name.txt', 'w') as f:
    for item in name_list:
        f.write("%s\n" % item)
