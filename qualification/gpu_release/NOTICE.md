# Marqov CUDA-Q workload candidate

This image adds Marqov's bounded circuit adapter to NVIDIA's released CUDA-Q runtime. It is not a Quantum Brilliance product or an endorsed partnership release.

Marqov/Qristal adapter source is distributed under the accompanying LICENSE.source (Apache-2.0). That license does not replace the licenses of NVIDIA or other bundled components. CUDA-Q's own LICENSE and NOTICE remain at /opt/nvidia/cudaq; the base container notices remain under /opt/nvidia/entrypoint.d; cuQuantum Python's license remains in its installed package. OS-package notices remain under /usr/share/doc. No upstream file is removed or relicensed by this layer.

The NVIDIA cuQuantum SDK license grants use and distribution subject to its conditions, including consistent downstream terms and protection of NVIDIA's rights. It prohibits modifying the SDK and removing its proprietary notices. NVIDIA's binaries in the base layers are unchanged. SDK terms: https://docs.nvidia.com/cuda/cuquantum/latest/license.html . Python bindings and SDK binaries have different terms. This notice does not grant rights beyond the applicable component licenses.

Retain and inspect the generated SPDX SBOM and the actual bundled notices when assessing distribution. Scanner output is not legal clearance, a vulnerability assessment, or evidence of complete source-license compliance. This candidate pipeline does not change package visibility or claim a supported public distribution.

Source and evidence: https://github.com/marqov-dev/qristal/tree/main/qualification/gpu_release . No hosted backend is enabled by publication. A new published digest must receive separate native GPU qualification before promotion.
