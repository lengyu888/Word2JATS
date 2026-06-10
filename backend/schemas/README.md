# Local JATS Publishing 1.4 schema

This directory intentionally does not bundle the large official JATS distribution.

Download the official JATS Publishing 1.4 RNG, XSD, or DTD package, keep all of its
relative include/module files together, and place it under this directory. The
validator scans recursively and prefers RNG, then XSD, then DTD.

If the distribution contains multiple schema modules, set `JATS_SCHEMA_PATH` to
the absolute path of its main schema file before starting FastAPI.

Without a local official schema, API responses report `jats_schema_valid: null` and
an explanatory `schema_errors` entry. They never claim formal JATS conformance.

## Installed schema in this workspace

The official `JATS-Publishing-1-4-MathML3-DTD.zip` package has been extracted to:

```text
backend/schemas/JATS-Publishing-1-4-MathML3-DTD/
```

The validator automatically discovers the main file:

```text
JATS-journalpublishing1-4-mathml3.dtd
```

Keep every `.dtd`, `.ent`, `.mod`, and supporting subdirectory together because
the main DTD loads them through relative paths.
