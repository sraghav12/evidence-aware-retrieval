import gzip,io,json,urllib.error
import pytest
from evaluation.evidence_aware.sec_collect import Client,latest_10k,collect

UA='Jane Doe jane.doe@example.org'
TICKERS={'0':{'cik_str':1234,'ticker':'ZZZ','title':'Zeta Holdings'}}
SUBS={'filings':{'recent':{'form':['10-K','10-Q','10-K/A','10-K','10-K','10-K'],'accessionNumber':['0001-25-1','0001-25-2','0001-25-3','0001-24-1','0001-23-1','0001-22-1'],
      'filingDate':['2025-02-10','2025-05-01','2025-03-01','2024-02-12','2023-02-13','2022-02-14'],'reportDate':['2024-12-31','2025-03-31','2024-12-31','2023-12-31','2022-12-31','2021-12-31'],
      'primaryDocument':['zzz-20241231.htm','q.htm','a.htm','zzz-20231231.htm','zzz-20221231.htm','zzz-20211231.htm']}}}


class FakeResponse(io.BytesIO):
    def __init__(self,body,gzipped=False):
        super().__init__(gzip.compress(body) if gzipped else body);self.headers={'Content-Encoding':'gzip'} if gzipped else {}
    def __enter__(self):return self
    def __exit__(self,*a):return False


class FakeNet:
    def __init__(self,fail_first=0):self.calls=[];self.fail_first=fail_first
    def __call__(self,request,timeout=None):
        self.calls.append((request.full_url,request.get_header('User-agent')))
        if self.fail_first:self.fail_first-=1;raise urllib.error.HTTPError(request.full_url,429,'slow down',{},None)
        url=request.full_url
        if url.endswith('company_tickers.json'):return FakeResponse(json.dumps(TICKERS).encode(),gzipped=True)
        if 'submissions' in url:return FakeResponse(json.dumps(SUBS).encode())
        return FakeResponse(b'<html>'+url.encode()+b'</html>')


def client(net,sleeps=None):
    clock=iter(range(0,10**6));sleeps=[] if sleeps is None else sleeps
    return Client(UA,opener=net,min_interval=0.25,sleep=sleeps.append,clock=lambda:next(clock)*0.0)


def test_user_agent_must_declare_name_and_email():
    for bad in ('','python-urllib','YourName your@email.com','Jane Doe'):
        with pytest.raises(ValueError):Client(bad)


def test_latest_annual_10k_excludes_amendments_and_quarters():
    f=latest_10k(SUBS,3)
    assert [x['accession_number'] for x in f]==['0001-25-1','0001-24-1','0001-23-1'] and f[0]['primary_document']=='zzz-20241231.htm'


def test_collect_downloads_rate_limited_with_declared_agent_and_hashes(tmp_path):
    net=FakeNet();sleeps=[];m=collect(client(net,sleeps),['ZZZ'],tmp_path,annual=2)
    assert all(ua==UA for _,ua in net.calls) and len(net.calls)==4 and sleeps and min(sleeps)>0
    doc=m['filings'][0]
    assert doc['doc_id']=='ZZZ_10K_2024' and doc['cik']=='1234' and doc['source_url']=='https://www.sec.gov/Archives/edgar/data/1234/0001251/zzz-20241231.htm'
    assert (tmp_path/'ZZZ_10K_2024.html').read_bytes().startswith(b'<html>') and len(doc['raw_sha256'])==64 and doc['raw_html_bytes']>0
    assert UA not in json.dumps(m) and 'jane' not in json.dumps(m).casefold()


def test_collect_reuses_cache_and_retries_throttling(tmp_path):
    collect(client(FakeNet()),['ZZZ'],tmp_path,annual=2)
    net=FakeNet(fail_first=1);m=collect(client(net),['ZZZ'],tmp_path,annual=2)
    assert sum('Archives' in u for u,_ in net.calls)==0 and all(f['status']=='cached' for f in m['filings'])
    assert net.calls[0][0]==net.calls[1][0]


def test_unknown_ticker_is_recorded_not_guessed(tmp_path):
    m=collect(client(FakeNet()),['NOPE'],tmp_path,annual=1)
    assert m['filings']==[] and m['missing']==[{'ticker':'NOPE','reason':'ticker_not_in_sec_list'}]
