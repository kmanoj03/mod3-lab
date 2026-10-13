#!/usr/bin/env bash
# Regenerates Python gRPC stubs from proto/inventory.proto into generated/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p generated
python -m grpc_tools.protoc \
  -I proto \
  --python_out=generated \
  --pyi_out=generated \
  --grpc_python_out=generated \
  proto/inventory.proto
echo "Generated stubs in grpc-version/generated/"
