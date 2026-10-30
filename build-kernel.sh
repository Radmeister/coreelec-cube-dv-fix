#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
kernel=$(cd "${1:?Use: bash build-kernel.sh BUILD_DIRECTORY/kernel}" && pwd)
for tool in gawk clang ld.lld llvm-ar llvm-nm llvm-objcopy make lzop; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool"; exit 1; }
done
if ! clang --version | head -1 | grep -q '17\.0\.6'; then
  echo 'Use the tested clang/lld 17.0.6 toolchain first in PATH.'; exit 1
fi
if ! ld.lld --version | grep -q '17\.0\.6'; then
  echo 'Use the tested clang/lld 17.0.6 toolchain first in PATH.'; exit 1
fi
if [[ "$(uname -m)" != aarch64 && "$(uname -m)" != arm64 ]]; then
  echo 'This script documents the tested native ARM64 Linux build. Review cross-build setup separately.'; exit 1
fi
if [[ "$(uname -s)" != Linux ]]; then echo 'Run the kernel build in Linux.'; exit 1; fi
# The original release generator uses GNU awk expressions. Select it explicitly.
temporary=$(mktemp -d)
trap 'rm -f "$temporary/awk"; rmdir "$temporary"' EXIT
ln -s "$(command -v gawk)" "$temporary/awk"
export PATH="$temporary:$PATH"
bash "$root/SOURCE/generate-gpio.sh" "$(dirname "$kernel")/bl30" "$kernel"
make -C "$kernel" ARCH=arm64 LLVM=1 LLVM_IAS=1 olddefconfig
make -C "$kernel" -j"${CUBE_BUILD_JOBS:-2}" ARCH=arm64 LLVM=1 LLVM_IAS=1 Image.lzo
echo "Built $kernel/arch/arm64/boot/Image.lzo; verify exports and review warnings before packaging."
