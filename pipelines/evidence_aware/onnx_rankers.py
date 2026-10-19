"""Optional pinned ONNX rankers for the dense, hybrid and rerank arms.
Imported only when such an arm is requested; the offline core stays standard-library only."""
from pathlib import Path
from time import perf_counter
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
ASSETS='data/release/v2/model_assets.json'
# bge-small-en-v1.5 model card: short retrieval queries take this instruction; passages do not.
QUERY_INSTRUCTION='Represent this sentence for searching relevant passages: '
MAX_TOKENS=512


class AssetMismatch(ValueError):pass


def verify(role):
    root=Path(role['local_dir']);root=root if root.is_absolute() else ROOT/root
    for f in role['files']:
        p=root/f['file']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:raise AssetMismatch(f"{role['repo']}: {f['file']} missing or SHA-256 mismatch")
    return root


class Encoder:
    def __init__(self,root):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.np=__import__('numpy')
        self.tokenizer=Tokenizer.from_file(str(root/'tokenizer.json'));self.tokenizer.enable_truncation(MAX_TOKENS);self.tokenizer.enable_padding()
        options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(root/'onnx/model.onnx'),options,providers=['CPUExecutionProvider'])

    def run(self,inputs):
        enc=self.tokenizer.encode_batch(inputs);np=self.np
        feed={'input_ids':np.array([e.ids for e in enc],dtype=np.int64),'attention_mask':np.array([e.attention_mask for e in enc],dtype=np.int64),'token_type_ids':np.array([e.type_ids for e in enc],dtype=np.int64)}
        return self.session.run(None,feed)[0],sum(min(len(e.ids),MAX_TOKENS) for e in enc)


class DenseRanker:
    """CLS-pooled, L2-normalized bge embeddings; units are embedded once, in sorted-ID batches, so scores do not depend on query order."""
    def __init__(self,root,revision,batch=32):
        self.encoder=Encoder(root);self.revision=revision;self.batch=batch;self.vectors={};self.queries=0
        self.index_stats={'units':0,'tokens':0,'seconds':0.0}

    def embed(self,texts):
        np=self.encoder.np;out=[];tokens=0
        for i in range(0,len(texts),self.batch):
            hidden,count=self.encoder.run(texts[i:i+self.batch]);tokens+=count
            cls=hidden[:,0,:];out.extend(cls/np.linalg.norm(cls,axis=1,keepdims=True))
        return out,tokens

    def index(self,units):
        todo=sorted({u.id:u for u in units if u.id not in self.vectors}.values(),key=lambda u:u.id)
        if not todo:return
        start=perf_counter();vectors,tokens=self.embed([u.text for u in todo])
        self.vectors.update({u.id:v for u,v in zip(todo,vectors)})
        self.index_stats['units']+=len(todo);self.index_stats['tokens']+=tokens;self.index_stats['seconds']+=perf_counter()-start

    def rank(self,question,units):
        self.index(units);query=self.embed([QUERY_INSTRUCTION+question])[0][0];self.queries+=1
        scores={u.id:round(float(self.vectors[u.id]@query),6) for u in units}
        return sorted(scores,key=lambda i:(-scores[i],i))

    def usage(self):return {'query_embeddings':self.queries,'indexed_units':self.index_stats['units']}


class CrossEncoderReranker:
    def __init__(self,root,revision,batch=16):self.encoder=Encoder(root);self.revision=revision;self.batch=batch;self.pairs=0;self.tokens=0

    def rank(self,question,units):
        scores={}
        for i in range(0,len(units),self.batch):
            chunk=units[i:i+self.batch];logits,count=self.encoder.run([(question,u.text) for u in chunk]);self.tokens+=count;self.pairs+=len(chunk)
            scores.update({u.id:round(float(x),6) for u,x in zip(chunk,logits[:,0])})
        return sorted(scores,key=lambda i:(-scores[i],i))

    def usage(self):return {'pairs':self.pairs,'tokens':self.tokens}


def revisions(assets_path=ROOT/ASSETS):
    """Verified pinned revisions without loading ONNX Runtime; empty when weights are absent or altered."""
    try:
        assets=json.loads(Path(assets_path).read_text());out={}
        for role,a in assets.items():verify(a);out[role]=f"{a['repo']}@{a['revision']}"
        return out
    except (OSError,AssetMismatch):return {}


def load_rankers(assets_path=ROOT/ASSETS,roles=('dense','reranker')):
    assets=json.loads(Path(assets_path).read_text());roots={r:verify(assets[r]) for r in roles}
    kinds={'dense':DenseRanker,'reranker':CrossEncoderReranker}
    return {r:kinds[r](roots[r],f"{assets[r]['repo']}@{assets[r]['revision']}") for r in roles}
