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
