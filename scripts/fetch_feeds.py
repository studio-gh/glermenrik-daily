import json,re,html,hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sources=json.loads((ROOT/'data/sources.json').read_text())

def clean(s):
    s=html.unescape(s or '')
    s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def parse(url):
    req=Request(url,headers={'User-Agent':'GlermenrikDaily/1.0'})
    with urlopen(req,timeout=20) as r:
        root=ET.fromstring(r.read())
    out=[]
    for e in list(root.findall('.//item'))+list(root.findall('.//{http://www.w3.org/2005/Atom}entry')):
        title=clean(e.findtext('title') or e.findtext('{http://www.w3.org/2005/Atom}title'))
        link=e.findtext('link') or ''
        atom_link=e.find('{http://www.w3.org/2005/Atom}link')
        if atom_link is not None:
            link=link or atom_link.attrib.get('href','')
        desc=clean(
            e.findtext('description')
            or e.findtext('{http://www.w3.org/2005/Atom}summary')
            or e.findtext('{http://purl.org/rss/1.0/modules/content/}encoded')
        )
        pub=e.findtext('pubDate') or e.findtext('{http://www.w3.org/2005/Atom}published') or e.findtext('{http://www.w3.org/2005/Atom}updated') or datetime.now(timezone.utc).isoformat()
        cats=[clean(c.text).upper() for c in e.findall('category') if c.text]

        image=''
        for node in [
            e.find('{http://search.yahoo.com/mrss/}content'),
            e.find('{http://search.yahoo.com/mrss/}thumbnail'),
            e.find('enclosure')
        ]:
            if node is not None:
                image=node.attrib.get('url') or node.attrib.get('href') or ''
                if image:
                    break

        if not image and desc:
            m=re.search(r'<img[^>]+src=[\'\"]([^\'\"]+)', e.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or '')
            image=m.group(1) if m else ''

        if title and link:
            out.append({
                'title':title,
                'description':desc[:500],
                'link':link,
                'pubDate':pub,
                'image':image,
                'categories':cats
            })
    return out

rows=[]
for s in sources:
    try:
        for x in parse(s['feed'])[:12]:
            x.update(
                source=s['name'],
                sourceUrl=s['url'],
                territory=s['territories'][0] if s.get('territories') else 'WILD',
                id=hashlib.sha256((s['name']+'|'+x['link']).encode()).hexdigest()[:16]
            )
            rows.append(x)
    except Exception as e:
        print('[WARN]',s['name'],e)

seen=set()
final=[]
for x in sorted(rows,key=lambda z:z.get('pubDate',''),reverse=True):
    key=x['link'].split('#')[0]
    if key in seen:
        continue
    seen.add(key)
    final.append(x)

(ROOT/'data/articles.json').write_text(json.dumps(final[:250],ensure_ascii=False,indent=2),encoding='utf-8')
print('Published',len(final[:250]),'references from',len(sources),'sources')