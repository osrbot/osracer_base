# Proto 1.1 sanitized fixtures

These fixtures describe public host-visible Proto 1.1 behavior only.

The historical behavior anchor is
`osrbot/osracer@c329c21614f0335d9a8c7a12d2e638a70293052f`. It remains an
accepted parser/behavior reference; it is not the active dependency or branch
for `osracer_base/main`.

- All identifiers and numeric telemetry values are synthetic.
- No firmware source, customer data, device serial number, calibration value, or site log is included.
- The samples are test evidence for framing, command order, RC/magnetometer units, covariance defaults, and timeout behavior; they are not vehicle profiles.
- Vehicle wheelbase, speed limits, steering limits, and other physical parameters must come from explicit `osracer_base` configuration.
- The accepted synchronized telemetry frame has exactly 18 whitespace-separated fields.
- Current mainline profile identity checks cover `neo`, `red`, and `blue` with
  schema `1`; the sanitized fixture values do not contain private firmware
  implementation details or product calibration.
