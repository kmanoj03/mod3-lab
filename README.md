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
