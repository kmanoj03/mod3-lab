# CMPE 273 – Module 3 Lab: REST vs gRPC

The same Order → Inventory interaction implemented two ways (Python track):

- **Order Service** – accepts an order (`item_id`, `quantity`) via `POST /orders`.
- **Inventory Service** – checks whether the requested item and quantity are available.

| Version | Order Service | Inventory Service | Order → Inventory |
|---------|---------------|-------------------|-------------------|
| REST    | Flask, port 8080 | Flask, port 8081 | HTTP + JSON, `requests` with timeout |
| gRPC    | Flask, port 9080 | gRPC server, port 50051 | gRPC with deadline |

## Layout

```
rest-version/
  inventory_service/   # REST Inventory Service
  order_service/       # Order Service calling Inventory over REST
grpc-version/
  proto/               # inventory.proto (service contract)
  inventory_service/   # gRPC Inventory Service
  order_service/       # Order Service calling Inventory over gRPC
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Seed inventory (in-memory, same in both versions): `apple: 10`, `banana: 5`, `laptop: 0`.

## Running the REST version

Run each service in its own terminal (with the venv activated) from the repo root:

```bash
# Terminal 1 – Inventory Service (port 8081)
python rest-version/inventory_service/app.py

# Terminal 2 – Order Service (port 8080)
python rest-version/order_service/app.py

# Terminal 3 – place an order
curl -i -X POST localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -d '{"item_id":"apple","quantity":3}'
```

Configuration (environment variables):

| Variable | Service | Default | Purpose |
|----------|---------|---------|---------|
| `INVENTORY_URL` | Order | `http://localhost:8081` | Inventory base URL |
| `INVENTORY_TIMEOUT_SECONDS` | Order | `2.0` | Timeout on the Order → Inventory request |
| `INVENTORY_DELAY_SECONDS` | Inventory | `0` | Artificial delay to simulate a slow Inventory |

### REST contract

`POST /inventory/check` (Inventory Service), JSON body `{"item_id": "apple", "quantity": 3}`:

| Status | Meaning |
|--------|---------|
| `200 OK` | Item exists and quantity is available |
| `400 Bad Request` | Missing/invalid `item_id` or `quantity` |
| `404 Not Found` | Unknown `item_id` |
| `409 Conflict` | Item exists but not enough stock |

`POST /orders` (Order Service) returns `201 Created` on success, passes through `400`/`404`/`409`
from Inventory, and returns `504 Gateway Timeout` if Inventory exceeds the timeout or
`503 Service Unavailable` if Inventory is unreachable.

## Running the gRPC version

The contract lives in [`grpc-version/proto/inventory.proto`](grpc-version/proto/inventory.proto).
Generated stubs are committed in `grpc-version/generated/`; regenerate them after editing the
proto with:

```bash
./grpc-version/generate.sh
```

Run each service in its own terminal (with the venv activated) from the repo root:

```bash
# Terminal 1 – Inventory Service (gRPC, port 50051)
python grpc-version/inventory_service/server.py

# Terminal 2 – Order Service (HTTP on port 9080, calls Inventory over gRPC)
python grpc-version/order_service/app.py

# Terminal 3 – place an order
curl -i -X POST localhost:9080/orders \
  -H 'Content-Type: application/json' \
  -d '{"item_id":"apple","quantity":3}'

# Or call the Inventory gRPC service directly
python grpc-version/client.py apple 3
```

Configuration (environment variables):

| Variable | Service | Default | Purpose |
|----------|---------|---------|---------|
| `INVENTORY_ADDR` | Order | `localhost:50051` | Inventory gRPC address |
| `INVENTORY_DEADLINE_SECONDS` | Order | `2.0` | gRPC deadline on the Order → Inventory call |
| `INVENTORY_DELAY_SECONDS` | Inventory | `0` | Artificial delay to simulate a slow Inventory |

### gRPC contract

`InventoryService.CheckInventory(CheckInventoryRequest) returns (CheckInventoryResponse)`:

| gRPC status | Meaning | Order Service HTTP status |
|-------------|---------|---------------------------|
| `OK` | Item exists and quantity is available | `201 Created` |
| `INVALID_ARGUMENT` | Empty `item_id` or `quantity <= 0` | `400 Bad Request` |
| `NOT_FOUND` | Unknown `item_id` | `404 Not Found` |
| `FAILED_PRECONDITION` | Item exists but not enough stock | `409 Conflict` |
| `DEADLINE_EXCEEDED` | Inventory did not answer within the deadline | `504 Gateway Timeout` |
| `UNAVAILABLE` | Inventory unreachable | `503 Service Unavailable` |
