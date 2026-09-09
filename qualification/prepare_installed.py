"""Prepare fixtures and copy-install the standalone adapter in an isolated workspace."""
from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
root=here.parents[1]
checks=root/'installed-checks';checks.mkdir(exist_ok=True)
(checks/'empty-backends.yaml').write_text('{}\n')
for name,source in [('core_cpu_smoke.py',here/'core_cpu_smoke.py'),('core_noise_smoke.py',here/'core_noise_smoke.py'),('integration_smoke.py',root/'qristal-integrations/qualification/cpu_smoke.py')]:
    checks.joinpath(name).write_text(source.read_text().replace('/work/qristal/qualification/empty-backends.yaml','/checks/empty-backends.yaml'))
for name in ('isolation.py','audit.py','decoder_smoke.cpp'):
    shutil.copy2(here/'installed'/name,checks/name)
(checks/'consumer').mkdir(exist_ok=True)
for name in ('CMakeLists.txt','main.cpp'):
    shutil.copy2(root/'qristal-core/tests/install_consumer'/name,checks/'consumer'/name)
installed=root/'install-integrations';installed.mkdir(exist_ok=True)
shutil.copy2(root/'qristal-integrations/qiskit_integration/qristal_primitives.py',installed/'qristal_primitives.py')
shutil.copy2(root/'qristal-integrations/LICENSE',installed/'LICENSE')
print('Prepared installed-only fixtures and standalone adapter module')
