import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import ShortlinkBypassEngine
from supported_sites import SUPPORTED_SITES
urls=[s.sample_url for s in SUPPORTED_SITES if s.host in {'oii.la','tpi.li','aii.sh'}]
for u in urls:
    t=time.perf_counter()
    res=ShortlinkBypassEngine(timeout=30).analyze(u)
    dt=time.perf_counter()-t
    d=res.to_dict(); d['elapsed_sec']=round(dt,3)
    print(json.dumps(d, ensure_ascii=False))
