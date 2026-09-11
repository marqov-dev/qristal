FROM nvcr.io/nvidia/quantum/cuda-quantum@sha256:cfd58fc868708a8f05944b87e89cc69665436dbcead29214753607d6e1f43f4a
USER root
COPY --chmod=0444 adapter.py fault_workload.py inventory.py payload.json /opt/marqov-qb/
RUN chmod 0755 /opt/marqov-qb
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1 NVIDIA_VISIBLE_DEVICES=void
WORKDIR /tmp
USER 65532:65532
RUN python3 -B -c "from pathlib import Path; [p.read_bytes() for p in Path('/opt/marqov-qb').iterdir()]"
ENTRYPOINT ["python3", "-B", "/opt/marqov-qb/adapter.py"]
