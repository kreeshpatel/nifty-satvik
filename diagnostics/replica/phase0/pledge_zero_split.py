"""Reproducible split of the promoter-pledge zeros in a frozen 400-filing sample.

The sample is frozen in pledge_sample_400.txt: the shareholding recordIds drawn with random.seed(1) and
random.sample(sorted list of the 6,232 XML files on disk at 2026-11-20 ~15:35 ET (fetch still running), 400). Re-running reads that list,
not the directory, so the counts do not move as more files are fetched.

It reports two classifications of the same 400 filings:
- v1: the first parser, which mapped a filing with no pledge field but a "pledged = false" flag to 0.
- v3: the current parser (build_risk_features.parse_pledge), which keeps such a filing NaN with a reason code.

    python diagnostics/replica/phase0/pledge_zero_split.py [--freeze]
"""
import collections
import gzip
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipelines" / "build"))
import build_risk_features as B  # noqa: E402

XML = ROOT / "data" / "shp_raw" / "xml"
LIST = Path(__file__).with_name("pledge_sample_400.txt")

if "--freeze" in sys.argv:
    files = sorted(p.name for p in XML.glob("*.xml.gz"))
    random.seed(1)
    LIST.write_text("\n".join(sorted(f.split(".")[0] for f in random.sample(files, 400))) + "\n", encoding="utf-8")
    print(f"froze 400 of {len(files)} files")

ids = LIST.read_text(encoding="utf-8").split()
v1, v3 = collections.Counter(), collections.Counter()
for rid in ids:
    x = gzip.open(XML / f"{rid}.xml.gz").read().decode("utf-8", "replace")
    val, why = B.parse_pledge(x)
    v3[why if val != val else (f"{why}:zero" if val == 0 else f"{why}:positive")] += 1
    v1["zero" if (val == 0 or why == "flag_false_no_field") else ("nan" if val != val else "positive")] += 1
print(json.dumps({"n": len(ids), "v1_parser": dict(v1), "v3_parser": dict(v3)}, indent=1, sort_keys=True))
