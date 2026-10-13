import logging
import os
import time

from flask import Flask, g, jsonify, request

SERVICE_NAME = "inventory-service-rest"
PORT = int(os.environ.get("PORT", "8081"))
# Artificial delay (seconds) applied to /inventory/check, used to demo timeouts.
DELAY_SECONDS = float(os.environ.get("INVENTORY_DELAY_SECONDS", "0"))

INVENTORY = {
    "apple": 10,
    "banana": 5,
    "laptop": 0,
}

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{SERVICE_NAME}] %(levelname)s %(message)s",
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
log = logging.getLogger(SERVICE_NAME)

app = Flask(__name__)


@app.before_request
def start_timer():
    g.start = time.perf_counter()


@app.after_request
def log_request(response):
    latency_ms = (time.perf_counter() - g.start) * 1000
    log.info(
        "method=%s path=%s status=%d latency_ms=%.1f",
        request.method, request.path, response.status_code, latency_ms,
    )
    return response


@app.get("/health")
def health():
    return jsonify(status="ok", service=SERVICE_NAME)


@app.post("/inventory/check")
def check_inventory():
    body = request.get_json(silent=True) or {}
    item_id = body.get("item_id")
    quantity = body.get("quantity")

    if not isinstance(item_id, str) or not item_id:
        return jsonify(error="item_id must be a non-empty string"), 400
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return jsonify(error="quantity must be a positive integer"), 400

    if DELAY_SECONDS > 0:
        log.warning("simulating slow response: sleeping %.1fs", DELAY_SECONDS)
        time.sleep(DELAY_SECONDS)

    if item_id not in INVENTORY:
        return jsonify(error=f"item '{item_id}' not found"), 404

    in_stock = INVENTORY[item_id]
    result = {
        "item_id": item_id,
        "requested_quantity": quantity,
        "available_quantity": in_stock,
        "available": in_stock >= quantity,
    }
    if not result["available"]:
        result["error"] = f"insufficient stock for '{item_id}'"
        return jsonify(result), 409
    return jsonify(result), 200


if __name__ == "__main__":
    log.info("starting on port %d (delay=%.1fs)", PORT, DELAY_SECONDS)
    app.run(host="0.0.0.0", port=PORT, threaded=True)
