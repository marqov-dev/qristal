"""Build the public Ubuntu toolchain in a bounded disposable container."""
import json, pathlib, subprocess, time, uuid
here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
base = json.loads((here / "source-lock.json").read_text())["ubuntu_base"]
name = "marqov-qristal-toolchain-" + uuid.uuid4().hex[:10]
start = time.monotonic()
try:
    with (root / "toolchain-build.log").open("w") as log:
        subprocess.run(["docker", "run", "--name", name, "--platform", "linux/amd64", "--cpus", "2", "--memory", "4g", "--memory-swap", "4g", "--pids-limit", "256", "--security-opt", "no-new-privileges", "--mount", f"type=bind,source={here / 'install-toolchain.sh'},target=/install-toolchain.sh,readonly", base, "/bin/sh", "/install-toolchain.sh"], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1200)
    image = subprocess.check_output(["docker", "commit", name], text=True).strip()
    subprocess.run(["docker", "cp", name + ":/toolchain-packages.txt", str(root / "toolchain-packages.txt")], check=True)
    (root / "toolchain.json").write_text(json.dumps(dict(base=base, image=image, platform="linux/amd64", seconds=time.monotonic()-start), indent=2))
    print(image)
finally:
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
