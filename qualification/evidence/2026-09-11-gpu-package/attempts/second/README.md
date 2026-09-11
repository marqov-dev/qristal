# Second packaging attempt

Improved diagnostics captured `python3: can't open file /opt/marqov-qb/inventory.py: [Errno 13] Permission denied`. The run stopped before circuit execution. The build succeeded but its non-root runtime could not read the package. The corrected recipe explicitly sets directory mode 0755 after COPY and checks readability under UID 65532 during the build. No simulator success is claimed from this attempt. Source hashes and the failing recipe are retained; unchanged Python files match the final source.
