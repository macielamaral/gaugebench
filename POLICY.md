# GaugeBench Policy v0.1

This document defines the benchmarking policy for GaugeBench runs.

## Scope

GaugeBench executes quantum benchmarks against gate-based and annealing backends.
All runs are local; no network egress is permitted during execution.

## Provenance

Every run produces a Content-Addressable Receipt (CAR) that cryptographically
binds the run configuration, source-code versions, and results together.

## Reproducibility

Runs are deterministic given the same inputs and engine versions.
The CAR receipt allows independent verification without a central server.
