#!/bin/bash
set -eupo pipefail

: ${D:="localhost"}
: ${PN:="thot"}
: ${PV:="latest"}
dockerfile="$(realpath Dockerfile)"
if command -v podman &>/dev/null; then
  : ${docker:="podman"}
else
  : ${docker:="docker"}
fi

T="$(mktemp -d -t docker-thot.XXXXXXX)"
trap "rm -rf '${T}'" EXIT

cp -ra ../../{setup.py,README.rst,src} "${T}/"
cd "${T}/"

${docker} build --rm --squash \
  --file "${dockerfile}" \
  --tag "${D}/${PN}:${PV}" \
  .
