"""Standard-library SEC EDGAR collector for held-out 10-K filings.
SEC requires a declared User-Agent with a real name and email; it is sent in headers and never written to disk."""
from pathlib import Path
import gzip,hashlib,json,re,time,urllib.error,urllib.request

TICKERS_URL='https://www.sec.gov/files/company_tickers.json'
SUBMISSIONS_URL='https://data.sec.gov/submissions/CIK{cik:010d}.json'
ARCHIVE_URL='https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}'
PLACEHOLDERS=('yourname','your@email','example@example')


class Client:
    """Rate-limited (default 4 requests/second, below SEC's 10/second ceiling) GET with bounded retries on throttling or server errors."""
    def __init__(self,user_agent,opener=urllib.request.urlopen,min_interval=0.25,sleep=time.sleep,clock=time.monotonic,retries=4):
        ua=(user_agent or '').strip()
        if not re.fullmatch(r'.*\S\s+[^@\s]+@[^@\s]+\.[A-Za-z]{2,}',ua) or any(p in ua.casefold() for p in PLACEHOLDERS):raise ValueError('SEC requires a User-Agent with a real name and email')
        self.user_agent=ua;self.opener=opener;self.min_interval=min_interval;self.sleep=sleep;self.clock=clock;self.retries=retries;self.last=None;self.requests=0

    def get(self,url):
        for attempt in range(self.retries+1):
            if self.last is not None:
                wait=self.min_interval-(self.clock()-self.last)
                if wait>0:self.sleep(wait)
            self.last=self.clock();self.requests+=1
            request=urllib.request.Request(url,headers={'User-Agent':self.user_agent,'Accept-Encoding':'gzip'})
            try:
                with self.opener(request,timeout=60) as response:
                    body=response.read()
                    return gzip.decompress(body) if response.headers.get('Content-Encoding')=='gzip' else body
            except urllib.error.HTTPError as e:
                if e.code not in (429,500,502,503,504) or attempt==self.retries:raise
                self.sleep(min(30,2**attempt))
        raise RuntimeError('unreachable')


def latest_10k(submissions,count):
    """Most recent original annual 10-K filings (no amendments) with an HTML primary document."""
    r=submissions['filings']['recent'];rows=[]
    for i,form in enumerate(r['form']):
        if form=='10-K' and r['primaryDocument'][i].endswith(('.htm','.html')):
            rows.append({'accession_number':r['accessionNumber'][i],'filing_date':r['filingDate'][i],'report_date':r['reportDate'][i],'primary_document':r['primaryDocument'][i]})
    return sorted(rows,key=lambda x:x['filing_date'],reverse=True)[:count]


def collect(client,tickers,out_dir,annual=3):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    listing={v['ticker'].upper():v for v in json.loads(client.get(TICKERS_URL)).values()}
    filings=[];missing=[]
    for ticker in tickers:
        entry=listing.get(ticker.upper())
        if entry is None:missing.append({'ticker':ticker,'reason':'ticker_not_in_sec_list'});continue
        cik=int(entry['cik_str']);subs=json.loads(client.get(SUBMISSIONS_URL.format(cik=cik)))
        chosen=latest_10k(subs,annual)
        if len(chosen)<annual:missing.append({'ticker':ticker,'reason':f'only {len(chosen)} annual 10-K filings'})
        for f in chosen:
            doc_id=f"{ticker.upper()}_10K_{f['report_date'][:4]}";path=out/f'{doc_id}.html'
            url=ARCHIVE_URL.format(cik=cik,accession=f['accession_number'].replace('-',''),document=f['primary_document'])
            status='cached' if path.is_file() else 'downloaded'
            if status=='downloaded':path.write_bytes(client.get(url))
            data=path.read_bytes()
            filings.append(dict(f,doc_id=doc_id,ticker=ticker.upper(),company_name=entry['title'],cik=str(cik),source_url=url,raw_html_bytes=len(data),raw_sha256=hashlib.sha256(data).hexdigest(),status=status))
    return {'schema_version':2,'source':'SEC EDGAR submissions API and Archives','rate_limit':f'min {client.min_interval}s between requests','requests':client.requests,'filings':filings,'missing':missing}


class FrozenMismatch(ValueError):pass


def collect_frozen(client,manifest,out_dir):
    """Reproduce a recorded collection: fetch exactly the recorded accessions (or reuse cached files) and require identical raw SHA-256."""
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);filings=[]
    for f in manifest['filings']:
        path=out/f'{f["doc_id"]}.html';status='verified'
        if not path.is_file():path.write_bytes(client.get(f['source_url']));status='downloaded_verified'
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=f['raw_sha256'] or len(data)!=f['raw_html_bytes']:raise FrozenMismatch(f'{f["doc_id"]}: raw HTML differs from the recorded collection')
        filings.append(dict(f,status='verified' if status=='verified' else status))
    return dict(manifest,filings=filings,requests=client.requests)
