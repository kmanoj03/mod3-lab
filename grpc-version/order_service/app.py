import logging
import os
import sys
import time
import uuid

import grpc
from flask import Flask, g, jsonify, request
from google.protobuf.json_format import MessageToDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "generated"))
import inventory_pb2  # noqa: E402
import inventory_pb2_grpc  # noqa: E402

SERVICE_NAME = "order-service-grpc"
PORT = int(os.environ.get("PORT", "9080"))
INVENTORY_ADDR = os.environ.get("INVENTORY_ADDR", "localhost:50051")
INVENTORY_DEADLINE_SECONDS = float(os.environ.get("INVENTORY_DEADLINE_SECONDS", "2.0"))

GRPC_TO_HTTP = {
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.FAILED_PRECONDITION: 409,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
}

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{SERVICE_NAME}] %(levelname)s %(message)s",
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
log = logging.getLogger(SERVICE_NAME)

channel = grpc.insecure_channel(INVENTORY_ADDR)
inventory_stub = inventory_pb2_grpc.InventoryServiceStub(channel)

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

    rpc_request = inventory_pb2.CheckInventoryRequest(item_id=item_id, quantity=quantity)
    try:
        rpc_response = inventory_stub.CheckInventory(
            rpc_request, timeout=INVENTORY_DEADLINE_SECONDS,
        )
    except grpc.RpcError as err:
        code = err.code()
        http_status = GRPC_TO_HTTP.get(code, 502)
        log.error(
            "CheckInventory failed: grpc_status=%s details=%r (item_id=%s, deadline=%.1fs)",
            code.name, err.details(), item_id, INVENTORY_DEADLINE_SECONDS,
        )
        payload = {
            "status": "REJECTED" if http_status in (400, 404, 409) else "FAILED",
            "error": err.details(),
            "grpc_status": code.name,
        }
        if code == grpc.StatusCode.DEADLINE_EXCEEDED:
            payload["error"] = "inventory service exceeded deadline"
            payload["deadline_seconds"] = INVENTORY_DEADLINE_SECONDS
        return jsonify(payload), http_status

    order = {
        "order_id": str(uuid.uuid4()),
        "status": "CONFIRMED",
        "item_id": item_id,
        "quantity": quantity,
        "inventory": MessageToDict(
            rpc_response,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=True,
        ),
    }
    return jsonify(order), 201


if __name__ == "__main__":
    log.info(
        "starting on port %d (inventory=%s, deadline=%.1fs)",
        PORT, INVENTORY_ADDR, INVENTORY_DEADLINE_SECONDS,
    )
    app.run(host="0.0.0.0", port=PORT, threaded=True)
