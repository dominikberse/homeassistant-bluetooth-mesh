FROM python:3.10-bookworm

RUN apt-get -y update && apt-get -y upgrade && apt-get -y install \
    build-essential \
    python3-docutils \
    udev \
    systemd \
    cmake \
    autoconf \
    libtool \
    libdbus-1-dev \
    libudev-dev \
    libical-dev \
    libreadline-dev

# install BlueZ with mesh support
WORKDIR /opt/build
COPY docker/scripts/install-ell.sh docker/scripts/install-json-c.sh docker/scripts/install-bluez.sh ./
RUN sed -i 's/\r$//' ./*.sh \
    && sh ./install-ell.sh \
    && cd /opt/build && sh ./install-json-c.sh \
    && cd /opt/build && sh ./install-bluez.sh

# install bridge from the local source tree (build context is the repository root)
WORKDIR /opt/hass-ble-mesh
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY gateway ./gateway

# mount config
WORKDIR /config
VOLUME /config

# run bluetooth service and bridge
WORKDIR /opt/hass-ble-mesh/gateway
COPY docker/scripts/entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh
ENTRYPOINT [ "/bin/bash", "entrypoint.sh" ]
