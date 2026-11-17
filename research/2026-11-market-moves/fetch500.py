import csv, json, os, time, urllib.parse, urllib.request
rows=list(csv.DictReader(open("lists/n500.csv"))); ok=0; bad=[]
for i,r in enumerate(rows):
    s=r["Symbol"].strip(); f="n500/%s.json"%s
    if os.path.exists(f) and os.path.getsize(f)>2000: ok+=1; continue
    url="https://query1.finance.yahoo.com/v8/finance/chart/%s.NS?period1=1388534400&period2=1800000000&interval=1d"%urllib.parse.quote(s)
    for attempt in range(3):
        try:
            raw=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read()
            j=json.loads(raw)
            if j["chart"]["result"]: open(f,"wb").write(raw); ok+=1; break
        except Exception as e:
            time.sleep(2+3*attempt)
    else: bad.append(s)
    time.sleep(0.25)
print("downloaded",ok,"of",len(rows),"| failed:",bad)
