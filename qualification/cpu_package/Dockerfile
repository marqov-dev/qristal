FROM ubuntu@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d
COPY apt-runtime.txt /tmp/apt-runtime.txt
RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive xargs apt-get install -y --no-install-recommends < /tmp/apt-runtime.txt \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /runtime-packages.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/apt-runtime.txt
COPY payload/ /
COPY inputs.json payload-inventory.json /opt/qristal/
RUN printf '{}\n' > /opt/qristal/empty-backends.yaml
ENV HOME=/tmp PYTHONNOUSERSITE=1 PYTHONPATH=/work/install-core/lib:/runtime/python-core:/work/install-integrations OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
USER 65532:65532
WORKDIR /tmp
ENTRYPOINT ["python3", "/opt/qristal/runtime.py"]
CMD ["--capabilities"]
LABEL org.opencontainers.image.title="Qristal public CPU experimental runtime"
