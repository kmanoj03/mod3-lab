# CMPE 273 – Module 3 Lab: REST vs gRPC

## Running the REST version

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 – Inventory Service (port 8081)
python rest-version/inventory_service/app.py

# Terminal 2 – Order Service (port 8080)
python rest-version/order_service/app.py

# Terminal 3 – place an order
curl -i -X POST localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -d '{"item_id":"apple","quantity":3}'
```

## Running the gRPC version

From the repo root (with the venv activated):

```bash
# Terminal 1 – Inventory Service (gRPC, port 50051)
python grpc-version/inventory_service/server.py

# Terminal 2 – Order Service (port 9080, calls Inventory over gRPC)
python grpc-version/order_service/app.py

# Terminal 3 – place an order
curl -i -X POST localhost:9080/orders \
  -H 'Content-Type: application/json' \
  -d '{"item_id":"apple","quantity":3}'

# Or call the Inventory gRPC service directly
python grpc-version/client.py apple 3
```

## Successful REST request and response

```
$ curl -s -i -X POST http://localhost:8080/orders -H 'Content-Type: application/json' -d '{"item_id":"apple","quantity":3}'
HTTP/1.1 201 CREATED
Content-Type: application/json

{"inventory":{"available":true,"available_quantity":10,"item_id":"apple","requested_quantity":3},"item_id":"apple","order_id":"b192424f-1a0e-45bc-8cb9-c8244b342095","quantity":3,"status":"CONFIRMED"}
```

## Successful gRPC request and response

```
$ python grpc-version/client.py apple 3
-> InventoryService/CheckInventory @ localhost:50051 (deadline=2.0s)
item_id: "apple"
quantity: 3
<- OK
item_id: "apple"
requested_quantity: 3
available_quantity: 10
available: true
```

## REST timeout handling

Inventory started with `INVENTORY_DELAY_SECONDS=5`; the Order Service timeout is 2 s.

```
$ curl -s -i -X POST http://localhost:8080/orders -H 'Content-Type: application/json' -d '{"item_id":"apple","quantity":1}'
HTTP/1.1 504 GATEWAY TIMEOUT
Content-Type: application/json

{"error":"inventory service timed out","timeout_seconds":2.0}

elapsed: 2.12s
```

```
19:13:01,313 [inventory-service-rest] WARNING simulating slow response: sleeping 5.0s
19:13:03,315 [order-service-rest] ERROR inventory call timed out after 2.0s (item_id=apple)
19:13:03,316 [order-service-rest] INFO method=POST path=/orders status=504 latency_ms=2005.1
```

## gRPC deadline handling

Inventory started with `INVENTORY_DELAY_SECONDS=5`; the gRPC deadline is 2 s.

```
$ curl -s -i -X POST http://localhost:9080/orders -H 'Content-Type: application/json' -d '{"item_id":"apple","quantity":1}'
HTTP/1.1 504 GATEWAY TIMEOUT
Content-Type: application/json

{"deadline_seconds":2.0,"error":"inventory service exceeded deadline","grpc_status":"DEADLINE_EXCEEDED","status":"FAILED"}

elapsed: 2.06s
```

```
19:13:14,736 [inventory-service-grpc] WARNING simulating slow response: sleeping 5.0s
19:13:16,738 [order-service-grpc] ERROR CheckInventory failed: grpc_status=DEADLINE_EXCEEDED details='Deadline Exceeded' (item_id=apple, deadline=2.0s)
19:13:16,739 [order-service-grpc] INFO method=POST path=/orders status=504 latency_ms=2005.2
```

## Order Service remains running after the failures

REST:

```
Order Service PID 32583 is still alive
$ curl -s -i http://localhost:8080/health
HTTP/1.1 200 OK

{"service":"order-service-rest","status":"ok"}
```

gRPC:

```
Order Service PID 32616 is still alive
$ curl -s -i http://localhost:9080/health
HTTP/1.1 200 OK

{"service":"order-service-grpc","status":"ok"}
```

## REST vs gRPC: what differed

With REST the contract was only a convention: the JSON field names, input validation, and the
choice of `404`/`409` lived only in hand-written code on each side, so nothing stopped the two
services from drifting apart. With gRPC the `.proto` file was the single source of truth and the
generated stubs gave typed request/response objects, at the cost of a code-generation step and
tight version coupling (the generated stubs required `grpcio>=1.84`). Errors also felt different:
REST let me pick any HTTP status and put details in a JSON body, while gRPC pushed me into its
fixed set of status codes (`NOT_FOUND`, `FAILED_PRECONDITION`, `DEADLINE_EXCEEDED`), which the
Order Service then had to translate back to HTTP for its own clients. Both timeouts failed cleanly
at about 2 s with a specific exception (`requests.Timeout` vs. `RpcError` with
`DEADLINE_EXCEEDED`), but the gRPC deadline is sent to the server with the call, whereas the
REST timeout exists only in the client. In both versions Inventory kept working for the full 5 s
and logged success after the caller had already given up. Finally, REST was much easier to
inspect and test with plain `curl`, while gRPC's binary protocol needed a dedicated client script.
