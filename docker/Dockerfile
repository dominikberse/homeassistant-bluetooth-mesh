FROM python:3.10-bullseye

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

WORKDIR /opt/hass-ble-mesh
COPY ./scripts/install-ell.sh .
RUN sh ./install-ell.sh

WORKDIR /opt/hass-ble-mesh
COPY ./scripts/install-json-c.sh .
RUN sh ./install-json-c.sh

RUN apt-get -y install 

WORKDIR /opt/hass-ble-mesh
COPY ./scripts/install-bluez.sh .
RUN sh ./install-bluez.sh

WORKDIR /opt/hass-ble-mesh
RUN git clone https://github.com/dominikberse/homeassistant-bluetooth-mesh.git
WORKDIR /opt/hass-ble-mesh/homeassistant-bluetooth-mesh
RUN pip3 install -r requirements.txt
COPY config.yaml .

WORKDIR /opt/hass-ble-mesh
COPY scripts/entrypoint.sh .
ENTRYPOINT [ "/bin/bash", "entrypoint.sh" ]