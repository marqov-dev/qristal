# Fresh Core native configure result

**Native qualification failed at configure.** This is a retained failure, not a
successful Core build or a hosted execution result. One approved temporary CPU
VM was used after three prelaunch transfer attempts; the successful multipart
upload preserved the exact original 314,255,079-byte input archive.

| Stage | Native observation |
| --- | --- |
| Builder | Public toolchain image built successfully (~88 seconds) |
| Input verification and staging | Passed; exact frozen materials accepted |
| XACC replay | Passed against the retained fresh-source installation |
| ANTLR | Offline wheel build passed (~3 seconds) |
| Python | Locked wheels installed; `pip check` passed (~21 seconds) |
| Core configure | Failed (~2.5 seconds) |
| Core compile/install/installed consumers | Not reached |

Core's `cmake/add_dependency.cmake:81` calls `is_in_install_path` with an
unquoted package-directory expansion. Our deliberate
`CMAKE_DISABLE_FIND_PACKAGE_*` flags leave that value unset, dropping an argument
and failing the macro for all eleven C++ dependencies. The later unknown
`pybind11_add_module` error follows from the dependency setup failure. This is an
existing helper weakness exposed by our forced-source invocation. It does not
show that public sources are missing, that XACC cannot link, or that Python is
incompatible with Core.

The next bounded correction quotes both path arguments and handles empty or
`*-NOTFOUND` paths before resolving them. Forced source selection and downstream
CPM/source audits stay enabled. A corrected preparation and another native run
are required before any Core success claim.

## Retained proof and cleanup

`output.tar.gz` contains the complete eight stage logs and their report/receipt,
without extracting arbitrary archive paths. SHA256:
`5735663a9b24251566b3e8896367a840a048e89e16f622cdff9d40ff88a3946f`
(34,116 bytes). The independent output verifier accepts its log/receipt bindings
and classifies it as a failed native result. `recovered.json` and `protocol.json`
preserve the original integrity chain. Resource aliases in transport/retention
metadata are descriptive only; exact resource identities remain in local state.

The runner verified VM and transfer cleanup. A separate AWS read independently
confirmed the instance terminated, volumes absent, security group absent and
bucket absent; see `independent-cleanup.json`. No resources are retained and no
second VM was launched.

The input archive remains:
`c1b393fa0f5e33fd34764834704afb6e6f8151afe2ee5ac68df65bd20231b9b7`.
The successful transport wrapper hash is recorded separately from the unchanged
native protocol in `multipart-transport.json`.

Related: platform #1701; packaging #609/#640/#1585/#1839. This result does not
complete those issues, qualify the commercial Emulator/internal vQPU, or alter
the platform's independent hosted admission work.
