# Image of the PySwitch build (see ../build and ../README.md): everything in one image, so the
# build program (builder/, Python) can run all steps: CircuitPython 7.3.1 build with frozen modules, the Python unit
# tests of PySwitch (Python >= 3.12) and the RAM measurement on an emulated RP2040 (Node, rp2040js).

## Stage 1: CircuitPython 7.3.1 sources and mpy-cross, built with the tools of Debian 12 ###########################
FROM debian:bookworm AS circuitpython

RUN apt-get update && apt-get install -y git make gcc gettext python3

# CircuitPython 7.3.1 sources (only the submodules needed for the raspberrypi port)
RUN git clone --depth 1 --branch 7.3.1 https://github.com/adafruit/circuitpython.git /opt/circuitpython
RUN cd /opt/circuitpython && \
    git config --file .gitmodules --get-regexp '\.path$' | awk '{ print $2 }' | grep -v -E '^(frozen|ports)/' > /tmp/submodules && \
    echo ports/raspberrypi/sdk >> /tmp/submodules && \
    git submodule update --init --depth 1 $(cat /tmp/submodules)

# mpy-cross (compiles the frozen modules)
RUN make -C /opt/circuitpython/mpy-cross -j

## Stage 2: the build image ######################################################################################
FROM node:22-trixie

RUN apt-get update && apt-get install -y \
    git \
    make \
    cmake \
    gettext \
    python3 \
    python3-pip \
    python3-coverage \
    curl \
    bzip2 \
    dosfstools \
    mtools

COPY --from=circuitpython /opt/circuitpython /opt/circuitpython

# Python packages of CircuitPython's build scripts
RUN cd /opt/circuitpython && (pip3 install --break-system-packages -r requirements-dev.txt || pip3 install --break-system-packages huffman cascadetoml jinja2 typer intelhex polib pyyaml setuptools_scm)

# ARM toolchain recommended for CircuitPython 7.x, for the architecture of the host (x86_64 or aarch64)
RUN curl -fL https://developer.arm.com/-/media/Files/downloads/gnu-rm/10.3-2021.10/gcc-arm-none-eabi-10.3-2021.10-$(uname -m)-linux.tar.bz2 \
    | tar -xj -C /opt
ENV PATH="/opt/gcc-arm-none-eabi-10.3-2021.10/bin:${PATH}"

# RP2040 emulator (https://github.com/wokwi/rp2040js, MIT licence, fixed version) for the RAM measurement
RUN git clone --depth 1 --branch v1.4.2 https://github.com/wokwi/rp2040js.git /opt/rp2040js
RUN cd /opt/rp2040js && npm install

# The mounted project folder belongs to the host user
RUN git config --global --add safe.directory '*'

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
