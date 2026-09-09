"""Fetch public CPU-probe inputs next to this checkout; never uses Git credentials."""
import hashlib, json, os, pathlib, shutil, subprocess, urllib.request
here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
lock = json.loads((here / "source-lock.json").read_text())
env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_TERMINAL_PROMPT="0")
def git(path, *args):
    return subprocess.check_output(["git", "-c", "credential.helper=", "-C", str(path), *args], env=env, text=True)
def checkout(name, url, commit):
    path = root / name
    if not path.exists():
        subprocess.run(["git", "-c", "credential.helper=", "clone", url, str(path)], env=env, check=True)
        git(path, "checkout", "--detach", commit)
    if git(path, "rev-parse", "HEAD").strip() != commit:
        raise RuntimeError(f"Refusing to change existing {name}: unexpected revision")
    return path
xacc = checkout("xacc", "https://github.com/eclipse-xacc/xacc.git", lock["xacc_commit"])
git(xacc, "submodule", "update", "--init", "--recursive")
actual = {line.strip().split()[1]: line.strip().split()[0].lstrip("+") for line in git(xacc, "submodule", "status", "--recursive").splitlines()}
expected = {line.strip().split()[1]: line.strip().split()[0] for line in lock["submodules"]}
if actual != expected:
    raise RuntimeError("Submodule revisions differ from source lock")
checkout("googletest", "https://github.com/google/googletest.git", lock["googletest_commit"])
core = checkout("qristal-core", "https://github.com/marqov-dev/qristal-core.git", lock["core_commit"])
for path, patch in [(core, here / "core-compatibility.patch"), (xacc, here / "xacc-cpu.patch"), (xacc / "tpls/cppmicroservices", here / "cppmicroservices.patch")]:
    check = subprocess.run(["git", "-C", str(path), "apply", "--reverse", "--check", str(patch)], capture_output=True)
    if check.returncode:
        git(path, "apply", "--check", str(patch))
        git(path, "apply", str(patch))
archive = root / "archives/boost_1_75_0.tar.bz2"
archive.parent.mkdir(exist_ok=True)
if not archive.exists():
    with urllib.request.urlopen("https://archives.boost.io/release/1.75.0/source/boost_1_75_0.tar.bz2", timeout=120) as response, archive.open("wb") as output:
        shutil.copyfileobj(response, output)
if hashlib.sha256(archive.read_bytes()).hexdigest() != lock["boost_sha256"]:
    raise RuntimeError("Boost archive checksum mismatch")
shutil.copy2(here / "acz_qpp_smoke.cpp", root / "acz_qpp_smoke.cpp")
print("Public CPU source inputs and patches verified")
