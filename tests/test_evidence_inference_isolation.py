import builtins,json,socket
from pathlib import Path
import pytest
from evaluation.evidence_aware.runner import run


def test_reference_file_open_forbidden_during_inference(tmp_path,monkeypatch):
    original=builtins.open
    def guarded(file,*args,**kwargs):
        if any(x in str(file) for x in ('references','gold_answers','diagnostic_specs')):raise AssertionError('gold access')
        return original(file,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',guarded)
    def network(*a,**k):raise AssertionError('network access')
    monkeypatch.setattr(socket.socket,'connect',network)
    out=run({'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':'tests/fixtures/evidence_v2/queries.jsonl','output':str(tmp_path/'out'),'provider_enabled':False,'max_usd':0})
    assert len((out/'traces.jsonl').read_text().splitlines())==8


def test_gold_fields_in_raw_cli_input_rejected(tmp_path):
    q=tmp_path/'bad.jsonl';q.write_text(json.dumps({'id':'q','question':'What?','as_of':'2025-01-01','gold_answer':'120'})+'\n')
    with pytest.raises(ValueError):run({'documents':'tests/fixtures/evidence_v2/documents.jsonl','queries':str(q),'output':str(tmp_path/'run')})
