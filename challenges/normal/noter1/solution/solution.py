import sys
import requests


if len(sys.argv) != 2:
	print('Usage: python solution.py <url>')
	sys.exit(1)

url = sys.argv[1]

s = requests.Session()
r = s.get(url)

for line in r.text.split("\n"):
    if "flag" in line:
        print(line)
