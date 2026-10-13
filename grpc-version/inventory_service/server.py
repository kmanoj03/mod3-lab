import logging
import os
import sys
import time
from concurrent import futures

import grpc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "generated"))
import inventory_pb2  # noqa: E402
import inventory_pb2_grpc  # noqa: E402

SERVICE_NAME = "inventory-service-grpc"
PORT = int(os.environ.get("PORT", "50051"))
# Artificial delay (seconds) applied to CheckInventory, used to demo deadlines.
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
log = logging.getLogger(SERVICE_NAME)


class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def CheckInventory(self, request, context):
        start = time.perf_counter()
        code = grpc.StatusCode.OK
        try:
            return self._check(request, context)
        except Exception:
            code = context.code() or grpc.StatusCode.UNKNOWN
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            log.info(
                "rpc=CheckInventory item_id=%s quantity=%d status=%s latency_ms=%.1f",
                request.item_id, request.quantity, code.name, latency_ms,
            )

    def _check(self, request, context):
        if not request.item_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "item_id must be a non-empty string")
        if request.quantity <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "quantity must be a positive integer")

        if DELAY_SECONDS > 0:
            log.warning("simulating slow response: sleeping %.1fs", DELAY_SECONDS)
            time.sleep(DELAY_SECONDS)

        if request.item_id not in INVENTORY:
            context.abort(grpc.StatusCode.NOT_FOUND, f"item '{request.item_id}' not found")

        in_stock = INVENTORY[request.item_id]
        if in_stock < request.quantity:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"insufficient stock for '{request.item_id}' "
                f"(requested {request.quantity}, available {in_stock})",
            )

        return inventory_pb2.CheckInventoryResponse(
            item_id=request.item_id,
            requested_quantity=request.quantity,
            available_quantity=in_stock,
            available=True,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryService(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    log.info("starting on port %d (delay=%.1fs)", PORT, DELAY_SECONDS)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
