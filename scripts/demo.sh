#!/usr/bin/env bash
# Reproduces the success + slow-inventory failure scenarios for one version.
#
# Usage: ./scripts/demo.sh rest|grpc
#
# Steps:
#   1. Start Inventory (no delay) and Order Service; place a successful order.
#   2. Restart Inventory with INVENTORY_DELAY_SECONDS=5 (> 2s timeout/deadline).
#   3. Place an order -> Order Service times out cleanly (504).
#   4. Show the same Order Service process is still alive and healthy.
#   5. Restart Inventory without delay; place another order -> succeeds again.
#   6. Dump both services' logs.
set -uo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-}"
DELAY=5
LOG_DIR="$(mktemp -d)"

case "$VERSION" in
  rest)
    INV_CMD=(python rest-version/inventory_service/app.py)
    ORDER_CMD=(python rest-version/order_service/app.py)
    ORDER_URL="http://localhost:8080"
    ;;
  grpc)
    INV_CMD=(python grpc-version/inventory_service/server.py)
    ORDER_CMD=(python grpc-version/order_service/app.py)
    ORDER_URL="http://localhost:9080"
    ;;
  *)
    echo "usage: $0 rest|grpc" >&2
    exit 2
    ;;
esac

if [[ -z "${VIRTUAL_ENV:-}" && -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

INV_PID=""
ORDER_PID=""
cleanup() {
  [[ -n "$INV_PID" ]] && kill "$INV_PID" 2>/dev/null
  [[ -n "$ORDER_PID" ]] && kill "$ORDER_PID" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT

section() { printf '\n========== %s ==========\n' "$1"; }

run() {
  printf '$ %s\n' "$*"
  "$@"
  printf '\n'
}

place_order() {
  local body="{\"item_id\":\"$1\",\"quantity\":$2}"
  printf "\$ curl -s -i -X POST %s/orders -H 'Content-Type: application/json' -d '%s'\n" \
    "$ORDER_URL" "$body"
  curl -s -i -X POST "$ORDER_URL/orders" -H 'Content-Type: application/json' -d "$body"
  printf '\n'
}

start_inventory() {
  INVENTORY_DELAY_SECONDS="$1" "${INV_CMD[@]}" >> "$LOG_DIR/inventory.log" 2>&1 &
  INV_PID=$!
  sleep 1.5
}

stop_inventory() {
  kill "$INV_PID" 2>/dev/null
  wait "$INV_PID" 2>/dev/null
  INV_PID=""
}

section "$VERSION: start Inventory (no delay) and Order Service"
start_inventory 0
"${ORDER_CMD[@]}" > "$LOG_DIR/order.log" 2>&1 &
ORDER_PID=$!
sleep 1.5
echo "Order Service PID: $ORDER_PID"

section "$VERSION: successful order"
place_order apple 3
if [[ "$VERSION" == "grpc" ]]; then
  section "grpc: direct CheckInventory call"
  run python grpc-version/client.py apple 3
fi

section "$VERSION: restart Inventory with ${DELAY}s delay"
stop_inventory
start_inventory "$DELAY"
echo "Inventory restarted with INVENTORY_DELAY_SECONDS=$DELAY"

section "$VERSION: order while Inventory is slow"
start=$(python -c 'import time; print(time.time())')
place_order apple 1
python -c "import time; print(f'elapsed: {time.time() - $start:.2f}s')"

section "$VERSION: Order Service still running after failure"
if kill -0 "$ORDER_PID" 2>/dev/null; then
  echo "Order Service PID $ORDER_PID is still alive"
else
  echo "Order Service PID $ORDER_PID is NOT running"
fi
run curl -s -i "$ORDER_URL/health"

section "$VERSION: Inventory back to normal, same Order Service process"
sleep "$DELAY"
stop_inventory
start_inventory 0
place_order banana 2
echo "Order Service PID $ORDER_PID alive: $(kill -0 "$ORDER_PID" 2>/dev/null && echo yes || echo no)"

section "$VERSION: Order Service log"
cat "$LOG_DIR/order.log"
section "$VERSION: Inventory Service log"
cat "$LOG_DIR/inventory.log"
