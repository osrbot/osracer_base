# Proto 1.1 sanitized fixtures

These fixtures describe public host-visible Proto 1.1 behavior only.

The behavior anchor is `osrbot/osracer@c329c21614f0335d9a8c7a12d2e638a70293052f`.

- All identifiers and numeric telemetry values are synthetic.
- No firmware source, customer data, device serial number, calibration value, or site log is included.
- The samples are test evidence for framing, command order, RC/magnetometer units, covariance defaults, and timeout behavior; they are not vehicle profiles.
- Vehicle wheelbase, speed limits, steering limits, and other physical parameters must come from explicit `osracer_base` configuration.
- The accepted synchronized telemetry frame has exactly 18 whitespace-separated fields.
