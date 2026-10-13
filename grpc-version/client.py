"""Calls the gRPC Inventory Service directly and prints the request/response.

Usage: python grpc-version/client.py <item_id> <quantity> [deadline_seconds]
"""
import os
import sys

import grpc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "generated"))
import inventory_pb2  # noqa: E402
import inventory_pb2_grpc  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__.strip())
        sys.exit(2)
    item_id, quantity = sys.argv[1], int(sys.argv[2])
    deadline = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    addr = os.environ.get("INVENTORY_ADDR", "localhost:50051")

    request = inventory_pb2.CheckInventoryRequest(item_id=item_id, quantity=quantity)
    print(f"-> InventoryService/CheckInventory @ {addr} (deadline={deadline}s)")
    print(request, end="")

    with grpc.insecure_channel(addr) as channel:
        stub = inventory_pb2_grpc.InventoryServiceStub(channel)
        try:
            response = stub.CheckInventory(request, timeout=deadline)
        except grpc.RpcError as err:
            print(f"<- {err.code().name}: {err.details()}")
            sys.exit(1)
    print("<- OK")
    print(response, end="")


if __name__ == "__main__":
    main()
