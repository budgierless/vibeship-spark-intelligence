import re
import sys
import requests

URL = sys.argv[1]
html = requests.get(URL, timeout=30).text
m = re.search(r'<h1 class="title mathjax">\s*<span class="descriptor">Title:</span>\s*(.*?)\s*</h1>', html, re.S)
print(m.group(1).strip() if m else 'NO_TITLE')
