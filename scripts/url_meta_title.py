import re
import sys
import requests

url = sys.argv[1]
html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
patterns = [
    r'citation_title" content="([^"]+)"',
    r'<meta property="og:title" content="([^"]+)"',
    r'<title>(.*?)</title>',
]
for pat in patterns:
    m = re.search(pat, html, re.I | re.S)
    if m:
        title = m.group(1).strip()
        title = re.sub(r"\s+", " ", title)
        print(title)
        raise SystemExit(0)
print("NO_TITLE")
