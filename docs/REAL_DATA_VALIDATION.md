# Real Shipment Data Validation

## Scope

The network optimizer remains a synthetic decision experiment. Its stress assumptions are now benchmarked separately against 10,324 public shipment records from the USAID Supply Chain Shipment Pricing Dataset. This does not claim that USAID's physical network is the modeled 65-node network.

## Evidence

- 43 destination countries, 73 vendors, and 4 shipment modes.
- On-time delivery rate: 88.5% across 10,324 dated shipments.
- Vendor lead-time P50/P90: 111/282 days.
- Freight-per-kg P50/P90: $7.26/$31.50.

Missing or non-numeric freight and weight fields are retained as missing rather than imputed. Mode and country outputs provide auditable operational benchmarks for scenario selection.
