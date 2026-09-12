"""Check a copied packet's internal consistency, not publisher authenticity."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

LIMIT = 32*1024*1024


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key]=value
    return result


def verify(path):
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        names=[i.filename for i in entries]
        if len(names)!=len(set(names)) or sum(i.file_size for i in entries)>LIMIT:
            raise ValueError("archive_bounds")
        if "manifest.json" not in names or archive.getinfo("manifest.json").file_size>65536:
            raise ValueError("manifest_missing_or_large")
        manifest=json.loads(archive.read("manifest.json"),object_pairs_hook=unique)
        if (set(manifest)!={"kind","revision","native_execution_performed_by_export","files","html_sha256"}
                or manifest["kind"]!="conference-evidence-subset"
                or manifest["native_execution_performed_by_export"] is not False
                or not re.fullmatch("[a-f0-9]{40}",manifest["revision"])):
            raise ValueError("manifest_scope")
        files=manifest["files"]
        if not isinstance(files,dict) or not 1<=len(files)<=100:
            raise ValueError("file_inventory")
        for name,digest in files.items():
            if (not isinstance(name,str) or name.startswith("/")
                    or "\\" in name or any(p in ("", ".", "..") for p in name.split("/"))
                    or not isinstance(digest,str) or not re.fullmatch("[a-f0-9]{64}",digest)):
                raise ValueError("file_inventory")
        if set(names)!={"index.html","manifest.json",*("evidence/"+n for n in files)}:
            raise ValueError("archive_inventory")
        expected={"index.html":manifest["html_sha256"],**{"evidence/"+n:d for n,d in files.items()}}
        for name,digest in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                raise ValueError("content_hash")
        return {"revision":manifest["revision"],"evidence_files":len(files),
                "internal_integrity":"verified","publisher_authenticity":"not_verified"}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    print(json.dumps(verify(parser.parse_args().archive),indent=2))
