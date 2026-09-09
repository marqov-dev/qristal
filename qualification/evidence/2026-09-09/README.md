# First public-toolchain CPU qualification

XACC commit d1edaa7ae53edc7e335f46d33160f93d6020aaa3 plus the included patches compiled with GCC 11.4.0 on public Ubuntu 22.04, Linux amd64 under emulation. The initial complete build took approximately 291 seconds. Installation initially exposed an omitted Boost_system target; the profile now includes it and the subsequent build/install passed. The retained build metadata describes that incremental correction.

The ACZ/qpp test passed: four deterministic interference circuits (1024 shots each) and a Bell circuit (522/502 correlated outcomes). Runtime error logs were rejected. No QB image or QB binary libraries were used. This qualifies the stated source/runtime slice, not Qristal Core, all simulators, performance, or a distributable release.

The acquisition/build/test scripts and source lock are in the parent qualification directory. The source-preparation script was rerun successfully against the pinned local inputs. The toolchain bootstrap wrapper reflects the same container commands used for this run; a second from-empty reproduction has not been performed.

## Core CPU extension

Core baseline a0bcfbf4e56adf443e981469e90013e999015183 plus core-compatibility.patch compiled and linked against the above public runtime. The initial Core/Python build took approximately 202 seconds; retained build metadata reflects the later diagnostic improvement. Eight 4096-shot fixtures passed: zero, X on each qubit, double H, Bell, GHZ, OpenQASM Bell and optimized Bell. Default output transpilation remained enabled. The test imports the rebuilt extension from the build tree, not an installed SDK image.

The runtime profile required public circuit optimizers, Staq, XASM and the two public Qristal transpiler plugins. An empty test backend database replaces the absent installed configuration. Earlier failures are retained as negative evidence; all were resolved for the stated fixtures. No claim is made for noise, tensor networks, GPU, Decoder, Integrations or production packaging.
