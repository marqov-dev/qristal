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
from identity import fingerprint, accepted, cleanup_owned

ROOT=HERE.parents[2]
IMAGE="sha256:432131e25d04d77dc4a5cacdf844de2f88f0d539fccfd283feb817ee5834a545"
BINARY=ROOT/"qristal-decoder/src/quantum_decoder.cpp"
OUT=Path(sys.argv[1])
OUT.mkdir()
name="qb-full-decoder-"+uuid.uuid4().hex
command=["docker","run","--pull","never","--name",name,"--label",f"qb.full-decoder={name}",
         "--platform","linux/amd64","--network","none","--cpus","2","--memory","4g",
         "--memory-swap","4g","--pids-limit","256","--read-only","--tmpfs","/tmp:rw,exec,size=128m",
         "--cap-drop","ALL","--security-opt","no-new-privileges","--user",f"{os.getuid()}:{os.getgid()}"]
for folder in ("build-core","install-core","install-xacc","qristal-decoder","deps/googletest/1aceeb1edcf0e5921c95e1fd1d7d8034132b5528"):
    command+=["--mount",f"type=bind,source={ROOT/folder},target=/work/{folder},readonly"]
command += ["--mount", f"type=bind,source={OUT},target=/probe"]
command+=["--workdir","/tmp","--entrypoint","/usr/bin/env",IMAGE,"-i",
          "PATH=/usr/local/bin:/usr/bin:/bin","HOME=/tmp","OMP_NUM_THREADS=2","OPENBLAS_NUM_THREADS=2",
          "/bin/sh", "-c", "c++ -std=c++17 -O1 -DNDEBUG /work/qristal-decoder/src/quantum_decoder.cpp /work/qristal-decoder/tests/FullDecoderInputValidation.cpp -I/work/qristal-decoder/include -I/work/install-xacc/include/xacc -I/work/install-xacc/include/quantum/gate -I/work/install-xacc/include -I/work/install-xacc/include/cppmicroservices4 -I/work/deps/googletest/1aceeb1edcf0e5921c95e1fd1d7d8034132b5528/googletest/include -L/work/install-xacc/lib -Wl,-rpath,/work/install-xacc/lib /work/build-core/lib/libgtest_main.a /work/build-core/lib/libgtest.a -lxacc -lxacc-quantum-gate -lCppMicroServices -ldl -lpthread -o /probe/input-tests && /probe/input-tests --gtest_filter=FullDecoderInputValidation.*"]
record={"kind":"full-decoder-input-validation-release","name":name,"image":IMAGE,
        "source_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=HERE).decode().strip(),
        "decoder_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT/"qristal-decoder").decode().strip(),
        "source_file_sha256":hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        "command":command,"timeout_seconds":180,"scope":"input validation only; no algorithm execution",
        "source_before":fingerprint(ROOT/"qristal-decoder")}
(OUT/"intent.json").write_text(json.dumps(record,indent=2)+"\n")
stdout=b""
try:
    code,stdout,stderr=capture(command,timeout=180,stdout_limit=65536,stderr_limit=16384)
    record["exit_code"]=code
    (OUT/"stdout.log").write_bytes(stdout)
    (OUT/"stderr.log").write_bytes(stderr)
except Exception as error:
    record["harness_error"]=type(error).__name__+":"+str(error)
finally:
    record.update(cleanup_owned(name))
    try:
        record["source_after"]=fingerprint(ROOT/"qristal-decoder")
    except OSError as error:
        record["identity_error"]=type(error).__name__
    record["qualified_input_validation"]=accepted(record, stdout)
    (OUT/"result.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))

sys.exit(0 if record.get("qualified_input_validation") else 1)
