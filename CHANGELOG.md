# Changelog

This file records the maintained OSRacer Base development line. Historical
commits and tags remain authoritative for released snapshots.

## Unreleased — package 0.2.0

### Changed

- On 2026-08-09, made `main` the default ROS 2 development line and retained
  `ros1` as a compatibility-only branch.
- Added explicit `neo`, `red`, and `blue` vehicle profile files and fail-closed
  firmware ProfileID/schema checks while keeping the public Proto 1.1 framing.
- Kept only ROS-side wheelbase, conservative speed limit, steering limit,
  frames, and battery display mapping in Base; firmware GPIO, encoder, PID,
  PWM, NVS, and hard safety settings remain outside this repository.
- Aligned downstream migration with the accepted
  `osracer@c329c21614f0335d9a8c7a12d2e638a70293052f` behavior and preserved
  its sanitized protocol fixtures.

### Validation

- GitHub Actions builds and tests `main` on ROS 2 Humble / Ubuntu 22.04 and
  ROS 2 Jazzy / Ubuntu 24.04.
- `osracer/main` pins
  `osracer_base@9b4e1a67ab755fa0a22dca7078b4b98c1b8cc3eb` for reproducible
  integration.

### Documentation

- Updated the maintenance baseline, clarified the historical c329 fixture
  anchor, and documented that `0.2.0` has no tag or release yet.

## 0.1.0 — 2026-08-07

- Established the first tagged ROS 2 Base package at
  `c7ba366084a56de32cb994048edd1e633090b69e`.
- Added the minimal chassis driver, udev binding, launch files, ROS topics, and
  the initial Humble/Jazzy CI baseline.
