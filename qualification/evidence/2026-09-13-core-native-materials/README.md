# Frozen Core native materials

Actual source-only assembly verified 9,294 entries covering the transformed Core
source, eleven prepared C++ dependencies, the retained fresh XACC installation
archive, fifty acquired Python wheels and ANTLR source/build tools, plus stage
helpers and installed-only consumer recipes. The compressed full manifest and
its hash are retained here. No setup script, compiler, Docker or AWS run occurred.

Four boundary tests and shell syntax checks pass; the complete offline replay
suite also passes. An independent review caught a filename-exclusion gap in the
source mutation audit, now fixed and covered by a regression assertion.

Native orchestration, actual dependency-selection verification, installed-only
execution and Core output retention remain unqualified. Core generates a header
in a source derivative and adds absolute plugin links to its XACC derivative;
these need explicit audits and retention handling. See core_native/README.md.
