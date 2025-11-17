import os, sys
from dotenv import load_dotenv

load_dotenv()
b = open('.env','rb').read()
print(".env bytes length:", len(b))
# show a hex dump of the whole file (or slice here if very large)
print(b.hex(' '))
# show the file lines (decoded with replacement so you can visually inspect)
for i,line in enumerate(open('.env', encoding='utf-8', errors='replace').read().splitlines(), 1):
    print(i, line)
