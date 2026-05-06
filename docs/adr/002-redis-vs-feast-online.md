# ADR-002: Redis Direct for Online Features Instead of Feast SDK

**Status:** Accepted  
**Date:** 2026-05-02  
**Context:** Online feature retrieval for real-time inference

## Decision

Compute velocity features directly from Redis keys rather than using the Feast SDK at inference time. Feast definitions exist for documentation and offline training compatibility only.

## Rationale

1. **Latency**: Feast's Redis online store adds ~5ms overhead for serialization/deserialization. Direct Redis key lookups are ~0.5ms.
2. **Simplicity**: No Feast SDK dependency in the inference path reduces the attack surface and deployment complexity.
3. **Feast limitations**: Feast is designed for batch/periodic materialization, not real-time streaming counter updates.

## Trade-offs

- Loses Feast's point-in-time correctness guarantees for online serving
- Velocity features are inherently approximate (sliding windows), so this is acceptable
- Feast definitions still serve as a feature catalog and documentation

## Alternatives Considered

- Full Feast SDK at inference — would add complexity without latency benefit for our use case
- Feast + Redis direct hybrid — what we ended up with
