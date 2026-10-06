import json,re,html,hashlib
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sources=json.loads((ROOT/'data/sources.json').read_text())

def clean(s):
    s=html.unescape(s or '')
    s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def classify(title,desc,source):
    t=(title+' '+desc).lower()
    rules=[
      ('AI', ['generative ai','artificial intelligence','ai assistant','ai agent','image model','video model','text-to-image','text to image','multimodal','model update','firefly','midjourney','veo','gemini','gpt-','claude','runway']),
      ('MOTION', ['motion','animation','video','after effects','premiere','lottie']),
      ('IMAGE', ['image','photo','photoshop','illustrator','visual','render']),
      ('DESIGN', ['design','figma','canva','typography','brand','creative cloud','indesign']),
      ('3D', ['3d','blender','geometry nodes','substance'])
    ]
    hits=[name for name,words in rules if any(w in t for w in words)]
    return hits or ['TECH']

class RSSParser:
    def __init__(self):
        self.items=[];self.cur=None;self.in_item=False;self.field=None
    def feed(self,raw):
        root=ET.fromstring(raw)
        for e in list(root.findall('.//item'))+list(root.findall('.//{http://www.w3.org/2005/Atom}entry')):
            title=clean(e.findtext('title') or e.findtext('{http://www.w3.org/2005/Atom}title'))
            link=e.findtext('link') or ''
            a=e.find('{http://www.w3.org/2005/Atom}link')
            if a is not None: link=link or a.attrib.get('href','')
            desc=clean(e.findtext('description') or e.findtext('{http://www.w3.org/2005/Atom}summary') or e.findtext('{http://purl.org/rss/1.0/modules/content/}encoded'))
            pub=e.findtext('pubDate') or e.findtext('{http://www.w3.org/2005/Atom}published') or e.findtext('{http://www.w3.org/2005/Atom}updated') or datetime.now(timezone.utc).isoformat()
            cats=[clean(c.text).upper() for c in e.findall('category') if c.text]
            image=''
            for node in [e.find('{http://search.yahoo.com/mrss/}content'),e.find('{http://search.yahoo.com/mrss/}thumbnail'),e.find('enclosure')]:
                if node is not None:
                    image=node.attrib.get('url') or node.attrib.get('href') or ''
                    if image: break
            if not image:
                raw_html=e.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or e.findtext('description') or ''
                m=re.search(r'<img[^>]+src=[\'\"]([^\'\"]+)',raw_html,re.I)
                image=m.group(1) if m else ''
            if title and link:self.items.append({'title':title,'description':desc[:500],'link':link,'pubDate':pub,'image':image,'categories':cats})
        return self.items

def fetch(url):
    req=Request(url,headers={'User-Agent':'GlermenrikDaily/1.1'})
    with urlopen(req,timeout=25) as r:return r.read()

def html_extract(raw,src):
    text_content=re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>',' ',raw.decode('utf-8','ignore'),flags=re.I|re.S)
    found=[]
    patterns=[
      r'<a[^>]+href=[\'\"]([^\'\"]+)[\'\"][^>]*>\s*(?:<[^>]+>\s*){0,3}([^<>]{12,180})',
      r'<h[1-3][^>]*>\s*([^<>]{12,180})\s*</h[1-3][^>]*>'
    ]
    for pat in patterns:
        for m in re.finditer(pat,text_content,flags=re.I):
            if len(m.groups())==2:
                link,title=m.group(1),clean(m.group(2))
                if link.startswith('/'): link=urljoin(src['url'],link)
            else:
                title=clean(m.group(1));link=src['url']
            if not title or title.lower() in {'read story','read more','discover more','learn more','home','news'}:continue
            if any(bad in link.lower() for bad in ['facebook','instagram','linkedin','youtube','twitter','mailto:']):continue
            found.append((title,link))
    # Prefer known article paths and remove obvious navigation
    cleaned=[];seen=set()
    for title,link in found:
        if src.get('product')=='Blender' and '/release' not in link.lower() and '/releases/' not in link.lower():continue
        if src.get('product')=='Midjourney' and 'updates.midjourney.com/' not in link.lower():continue
        if src.get('product')=='Canva' and '/newsroom/news/' not in link.lower():continue
        if src.get('product') in ('Adobe','Firefly') and '/publish/' not in link.lower():continue
        key=(title,link)
        if key in seen:continue
        seen.add(key);cleaned.append((title,link))
    return cleaned[:18]

rows=[]
for s in sources:
    try:
        items=[]
        if s.get('feed'):
            items=RSSParser().feed(fetch(s['feed']))
        else:
            for title,link in html_extract(fetch(s['url']),s):
                items.append({'title':title,'description':'Official update from '+s['product'],'link':link,'pubDate':'','fetchedAt':datetime.now(timezone.utc).isoformat(),'image':'','categories':[]})
        for x in items[:15]:
            cats=list(dict.fromkeys((s.get('territories') or [])+classify(x['title'],x.get('description',''),s['name'])+(x.get('categories') or [])))
            x.update(source=s['name'],sourceUrl=s['url'],sourceKind=s.get('kind','culture'),product=s.get('product',''),territory=s.get('territories',['WILD'])[0],categories=cats,id=hashlib.sha256((s['name']+'|'+x['link']).encode()).hexdigest()[:16])
            # Keep software and AI updates visually distinct in the app.
            if s.get('kind') in ('software','ai'): x['section']='TOOL WATCH' if s.get('kind')=='software' else 'AI IMPACT'
            else: x['section']='CULTURE'
            rows.append(x)
    except Exception as e:
        print('[WARN]',s['name'],e)

seen=set();final=[]
for x in sorted(rows,key=lambda z:z.get('pubDate',''),reverse=True):
    key=x['link'].split('#')[0]
    if key in seen:continue
    seen.add(key);final.append(x)

# Light relevance pass for AI: keep creative/design-impacting items ahead of generic AI business news.
creative_terms=['design','creative','image','video','visual','art','photoshop','illustrator','figma','canva','blender','firefly','midjourney','runway','motion','typography','brand','creator','content','camera','music']
for x in final:
    blob=(x['title']+' '+x.get('description','')+' '+' '.join(x.get('categories',[]))).lower()
    x['creativeScore']=sum(1 for term in creative_terms if term in blob)
    if x['sourceKind']=='ai' and x['creativeScore']<1:x['creativeScore']=0
final.sort(key=lambda x:(x.get('sourceKind')=='ai',x.get('creativeScore',0),x.get('pubDate','')),reverse=True)

(ROOT/'data/articles.json').write_text(json.dumps(final[:350],ensure_ascii=False,indent=2),encoding='utf-8')
print('Published',len(final[:350]),'references from',len(sources),'sources.')