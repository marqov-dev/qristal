#!/bin/sh
# Marqov community qualification toolchain; no QB binaries are used.
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends build-essential gfortran cmake ninja-build git ca-certificates curl libboost-all-dev libopenblas-dev libssl-dev libcurl4-openssl-dev libeigen3-dev python3-dev python3-venv python3-pip pkg-config unzip
dpkg-query -W > /toolchain-packages.txt
rm -rf /var/lib/apt/lists/*
