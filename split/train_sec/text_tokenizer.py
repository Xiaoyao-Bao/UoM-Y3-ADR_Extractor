files = open('train_sec_file_name.txt', "r").read().split('\n')
for filename in files:
    f = open(filename)
    raw = f.read()
    print(raw)
    break