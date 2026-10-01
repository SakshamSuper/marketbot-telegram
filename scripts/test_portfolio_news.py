import urllib.parse
import requests
import feedparser

companies = [
    "Vedanta",
    "State Bank of India",
    "BSE Limited",
    "Bharat Electronics",
    "Mazagon Dock",
    "Axis Bank",
    "HDFC Bank",
    "Bharti Airtel",
    "Coal India",
    "Drone Destination",
    "IRFC",
]

query = " OR ".join(f'"{c}"' for c in companies[:6])
encoded_q = urllib.parse.quote(query)
url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
r = requests.get(url, headers=headers, timeout=8)
feed = feedparser.parse(r.content)

print(f"Total articles returned: {len(feed.entries)}")
for i, entry in enumerate(feed.entries[:10], 1):
    print(f"{i}. {entry.title}")
