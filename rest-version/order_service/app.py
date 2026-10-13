import logging
import os
import time
import uuid

import requests
from flask import Flask, g, jsonify, request

SERVICE_NAME = "order-service-rest"
PORT = int(os.environ.get("PORT", "8080"))
INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://localhost:8081")
INVENTORY_TIMEOUT_SECONDS = float(os.environ.get("INVENTORY_TIMEOUT_SECONDS", "2.0"))

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


@app.post("/orders")
def create_order():
    body = request.get_json(silent=True) or {}
    item_id = body.get("item_id")
    quantity = body.get("quantity")

    if not isinstance(item_id, str) or not item_id:
        return jsonify(error="item_id must be a non-empty string"), 400
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        return jsonify(error="quantity must be a positive integer"), 400

    try:
        resp = requests.post(
            f"{INVENTORY_URL}/inventory/check",
            json={"item_id": item_id, "quantity": quantity},
            timeout=INVENTORY_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        log.error(
            "inventory call timed out after %.1fs (item_id=%s)",
            INVENTORY_TIMEOUT_SECONDS, item_id,
        )
        return jsonify(
            error="inventory service timed out",
            timeout_seconds=INVENTORY_TIMEOUT_SECONDS,
        ), 504
    except requests.ConnectionError as exc:
        log.error("inventory service unreachable: %s", exc)
        return jsonify(error="inventory service unavailable"), 503

    try:
        inventory = resp.json()
    except ValueError:
        log.error("inventory returned non-JSON response (status=%d)", resp.status_code)
        return jsonify(error="invalid response from inventory service"), 502

    if resp.status_code == 200:
        order = {
            "order_id": str(uuid.uuid4()),
            "status": "CONFIRMED",
            "item_id": item_id,
            "quantity": quantity,
            "inventory": inventory,
        }
        return jsonify(order), 201
    if resp.status_code in (400, 404, 409):
        return jsonify(
            status="REJECTED",
            error=inventory.get("error", "order rejected by inventory"),
            inventory=inventory,
        ), resp.status_code

    log.error("unexpected inventory status %d", resp.status_code)
    return jsonify(error="unexpected response from inventory service"), 502


if __name__ == "__main__":
    log.info(
        "starting on port %d (inventory=%s, timeout=%.1fs)",
        PORT, INVENTORY_URL, INVENTORY_TIMEOUT_SECONDS,
    )
    app.run(host="0.0.0.0", port=PORT, threaded=True)
