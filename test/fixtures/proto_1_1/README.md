# Proto 1.1 Public Fixtures

These fixtures describe public host-visible Proto 1.1 behavior only.

The machine-readable fixture records its exact behavior anchor for deterministic
parser regression. That provenance field is test metadata, not a runtime
dependency or installation instruction.

- All identifiers and numeric telemetry values are synthetic.
- No firmware source, device serial number, calibration value, or site log is
  included.
- The samples cover framing, command order, sensor units, covariance defaults,
  and timeout behavior; they are not vehicle configurations.
- ROS geometry and operating limits come from explicit OSRacer Base vehicle
  configuration files.
- The synchronized telemetry frame has exactly 18 whitespace-separated fields.
- `firmware_contract.json` defines the public protocol version, command units,
  configuration identity, and schema used by host compatibility tests.
