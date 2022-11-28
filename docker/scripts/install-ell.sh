#
# Docker helper script to get Embedded Linux library
#
set -e

# clone repository
git clone https://git.kernel.org/pub/scm/libs/ell/ell.git
cd ell

# checkout recent version
git checkout 0.54