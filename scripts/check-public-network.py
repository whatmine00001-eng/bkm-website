#!/usr/bin/env python3
"""Read-only public connectivity diagnostic. No CRM, credentials, lead submission or DNS writes."""
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import socket
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse

OUT=Path('network-review'); OUT.mkdir(exist_ok=True)
HEADERS={'User-Agent':'BKM-owner-connectivity-diagnostic/1.0','Cache-Control':'no-cache'}
class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self): self.hops=[]
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.hops.append({'code':code,'to':newurl})
        if urllib.parse.urlsplit(newurl).hostname not in ('24bkm.com','www.24bkm.com'):
            raise ValueError('Unexpected redirect host')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def http(url):
    h=Redirects(); op=urllib.request.build_opener(h); start=time.monotonic()
    try:
        with op.open(urllib.request.Request(url,headers=HEADERS),timeout=15) as r:
            data=r.read(1000000)
            result={'url':url,'status':r.status,'final':r.url,'redirects':h.hops,'bytes':len(data),'seconds':round(time.monotonic()-start,2),'headers':{k:v for k,v in r.headers.items() if k.lower() not in ('set-cookie',)}}
            if url=='https://24bkm.com/':
                text=data.decode('utf-8','replace')
                import re
                result['page_title']=(re.findall('<title>(.*?)</title>',text,re.S) or [''])[0]
                result['external_hosts']=sorted(set(urllib.parse.urlsplit(u).hostname for u in re.findall(r'(?:href|src)=[\"\'](https?://[^\"\']+)',text)))
            return result
    except urllib.error.HTTPError as e: return {'url':url,'status':e.code,'redirects':h.hops,'error':str(e)}
    except Exception as e: return {'url':url,'error':str(e)}

def dns(job):
    provider,name,kind=job
    base='https://dns.google/resolve' if provider=='Google' else 'https://cloudflare-dns.com/dns-query'
    url=base+'?'+urllib.parse.urlencode({'name':name,'type':kind})
    try:
        req=urllib.request.Request(url,headers={'Accept':'application/dns-json','User-Agent':HEADERS['User-Agent']})
        with urllib.request.urlopen(req,timeout=12) as r: value=json.load(r)
        return {'resolver':provider,'name':name,'type':kind,'status':value.get('Status'),'dnssec_validated':value.get('AD'),'answer':value.get('Answer',[])}
    except Exception as e:return {'resolver':provider,'name':name,'type':kind,'error':str(e)}

def tls(job):
    host,version=job
    try:
        ctx=ssl.create_default_context(); ctx.minimum_version=version; ctx.maximum_version=version
        ctx.set_alpn_protocols(['h2','http/1.1'])
        with socket.create_connection((host,443),timeout=12) as raw:
            with ctx.wrap_socket(raw,server_hostname=host) as conn:
                cert=conn.getpeercert()
                return {'host':host,'requested':version.name,'tls':conn.version(),'alpn':conn.selected_alpn_protocol(),'peer':conn.getpeername()[0],'certificate_valid':True,'not_after':cert.get('notAfter'),'names':[v for k,v in cert.get('subjectAltName',[]) if k=='DNS']}
    except Exception as e:return {'host':host,'requested':version.name,'error':str(e)}

urls=['https://24bkm.com/','https://www.24bkm.com/','http://24bkm.com/','http://www.24bkm.com/','https://24bkm.com/index.html','https://24bkm.com/services.html','https://24bkm.com/assets/site-config.js','https://24bkm.com/services']
queries=[(r,h,t) for r in ('Google','Cloudflare') for h in ('24bkm.com','www.24bkm.com') for t in ('A','AAAA')]+[('Google','24bkm.com','NS'),('Google','24bkm.com','DS')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: d=list(pool.map(dns,queries))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: h=list(pool.map(http,urls))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: t=list(pool.map(tls,[(x,v) for x in ('24bkm.com','www.24bkm.com') for v in (ssl.TLSVersion.TLSv1_2,ssl.TLSVersion.TLSv1_3)]))
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runner':os.environ.get('RUNNER_OS','unknown'),'note':'Independent cloud runner, NOT the user VPN. Successful checks do not prove global reachability.','dns':d,'http':h,'tls':t}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for row in d:print('DNS',row['resolver'],row['name'],row['type'],row.get('status'),json.dumps(row.get('answer',row.get('error')),ensure_ascii=False))
for row in h:print('HTTP',row['url'],row.get('status'),row.get('final'),json.dumps(row.get('redirects',row.get('error')),ensure_ascii=False))
for row in t:print('TLS',json.dumps(row,ensure_ascii=False))
print('NETWORK_READ_ONLY_COMPLETE: no hosting, security or DNS changes; no VPN-specific diagnosis without the failing path.')
