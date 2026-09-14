FROM ubuntu@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d AS prepared
COPY os/debs/ /inputs/debs/
RUN DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=0 --no-install-recommends -y install /inputs/debs/*.deb \
    && apt-get check \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /runtime-packages.txt \
    && rm -rf /inputs/debs /var/lib/apt/lists/*
COPY work.tar /inputs/work.tar
RUN mkdir -p /work && tar -xf /inputs/work.tar -C /work && rm /inputs/work.tar
COPY runtime/ /opt/qristal/
COPY python/wheels/ /inputs/wheels/
COPY runtime/requirements.txt /inputs/requirements.txt
RUN PIP_FORCE_REINSTALL=1 sh /opt/qristal/install-python.sh && rm -rf /inputs/wheels /inputs/requirements.txt
ENV HOME=/tmp PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/install-core/lib:/work/install-core/python-site OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
USER 65532:65532
WORKDIR /tmp
ENTRYPOINT ["/work/python-core/bin/python", "/opt/qristal/qpp_runtime.py"]
CMD ["--capabilities"]
LABEL org.opencontainers.image.title="Source-built Qristal QPP local qualification candidate"
