"""Bounded diagnostic of the existing full decoder fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"runtime"))
from bounded_process import capture

ROOT=HERE.parents[2]
IMAGE="sha256:432131e25d04d77dc4a5cacdf844de2f88f0d539fccfd283feb817ee5834a545"
BINARY=ROOT/"build-core/decoder/CITests_decoder"
OUT=Path(sys.argv[1])
OUT.mkdir()
name="qb-full-decoder-"+uuid.uuid4().hex
command=["docker","run","--pull","never","--name",name,"--label",f"qb.full-decoder={name}",
         "--platform","linux/amd64","--network","none","--cpus","2","--memory","4g",
         "--memory-swap","4g","--pids-limit","256","--read-only","--tmpfs","/tmp:rw,exec,size=128m",
         "--cap-drop","ALL","--security-opt","no-new-privileges","--user",f"{os.getuid()}:{os.getgid()}"]
for folder in ("build-core","install-core","install-xacc"):
    command+=["--mount",f"type=bind,source={ROOT/folder},target=/work/{folder},readonly"]
command+=["--workdir","/tmp","--entrypoint","/usr/bin/env",IMAGE,"-i",
          "PATH=/usr/local/bin:/usr/bin:/bin","HOME=/tmp","OMP_NUM_THREADS=2","OPENBLAS_NUM_THREADS=2",
          "/work/build-core/decoder/CITests_decoder",
          "--gtest_filter=QuantumDecoderCanonicalAlgorithm.checkSimple"]
record={"kind":"full-decoder-existing-fixture-diagnostic","name":name,"image":IMAGE,
        "source_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=HERE).decode().strip(),
        "decoder_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT/"qristal-decoder").decode().strip(),
        "binary_sha256":hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        "command":command,"timeout_seconds":60,"correctness_assertion_present":False}
(OUT/"intent.json").write_text(json.dumps(record,indent=2)+"\n")
try:
    code,stdout,stderr=capture(command,timeout=60,stdout_limit=65536,stderr_limit=16384)
    record["exit_code"]=code
    (OUT/"stdout.log").write_bytes(stdout)
    (OUT/"stderr.log").write_bytes(stderr)
except Exception as error:
    record["harness_error"]=type(error).__name__+":"+str(error)
finally:
    ids=subprocess.check_output(["docker","ps","-aq","--filter",f"name=^/{name}$",
                                  "--filter",f"label=qb.full-decoder={name}"]).decode().split()
    for identity in ids:
        subprocess.run(["docker","rm","-f",identity],check=True,capture_output=True,timeout=30)
    remaining=subprocess.check_output(["docker","ps","-aq","--filter",f"name=^/{name}$",
                                        "--filter",f"label=qb.full-decoder={name}"]).decode().strip()
    record["owned_container_absent"]=not remaining
    (OUT/"result.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))
