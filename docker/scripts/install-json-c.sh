#
# Docker helper script to install json-c
#
set -e

# clone recent version
wget https://github.com/json-c/json-c/archive/refs/tags/json-c-0.16-20220414.tar.gz
tar -xvf json-c-0.16-20220414.tar.gz
cd json-c-json-c-0.16-20220414/

# configure
mkdir json-c-build
cd json-c-build/
cmake -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_STATIC_LIBS=OFF ..

# build and install
make
make install