#!/bin/sh
# Download-only resolver inside the exact disposable Ubuntu amd64 base.
set -eu
export DEBIAN_FRONTEND=noninteractive LC_ALL=C
[ "$(dpkg --print-architecture)" = amd64 ]
test -f /usr/share/keyrings/ubuntu-archive-keyring.gpg
test -d /output
cp /var/lib/dpkg/status /output/base-status
cp /usr/share/keyrings/ubuntu-archive-keyring.gpg /output/ubuntu-archive-keyring.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://snapshot.ubuntu.com/ubuntu/20260913T000000Z jammy main universe' 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://snapshot.ubuntu.com/ubuntu/20260913T000000Z jammy-updates main universe' 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://snapshot.ubuntu.com/ubuntu/20260913T000000Z jammy-security main universe' > /etc/apt/sources.list
rm -f /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list
cp /etc/apt/sources.list /output/sources.list
apt-get -o APT::Update::Error-Mode=any -o Acquire::https::CaInfo=/trust.pem -o Acquire::Retries=1 -o Acquire::https::Timeout=30 update
apt-get -o Acquire::https::CaInfo=/trust.pem --download-only --reinstall --no-install-recommends -y install \
 python3.10=3.10.12-1~22.04.18 python3.10-venv=3.10.12-1~22.04.18 \
 libpython3.10=3.10.12-1~22.04.18 libgomp1 libopenblas0-pthread \
 libcurl4 libssl3 libstdc++6 libgfortran5 ca-certificates
mkdir /output/debs /output/lists
cp /var/cache/apt/archives/*.deb /output/debs/
find /var/lib/apt/lists -maxdepth 1 -type f ! -name lock -exec cp '{}' /output/lists/ ';'
cp /var/lib/dpkg/status /output/after-status
cmp /output/base-status /output/after-status
printf '%s\n' 'download-only: dpkg installed state unchanged' > /output/completed.txt

mkdir /output/indexes
for index in /var/lib/apt/lists/*_Packages*; do
 /usr/lib/apt/apt-helper cat-file "$index" | gzip -n > "/output/indexes/$(basename "$index").gz"
done
for file in /output/debs/*.deb; do
 printf '%s\t' "$(basename "$file")"
 dpkg-deb -f "$file" Package Version Architecture | tr '\n' '\t'
 printf '\n'
done > /output/package-fields.tsv
tar -cf /output/base-docs.tar /usr/share/doc /usr/share/common-licenses
