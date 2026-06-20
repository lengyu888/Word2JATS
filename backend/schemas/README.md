# Local JATS Publishing Schemas

This workspace bundles local JATS DTD files so formal validation can run offline.

## Default Competition Schema

The default delivery target is JATS Publishing 1.3 with MathML3. The official DTD package is extracted to:

```text
backend/schemas/JATS-Publishing-1-3-MathML3-DTD/
```

Main DTD:

```text
JATS-journalpublishing1-3-mathml3.dtd
```

Generated XML uses:

```xml
<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD with MathML3 v1.3 20210610//EN" "JATS-journalpublishing1-3-mathml3.dtd">
```

## Compatibility Schema

The previous JATS Publishing 1.4 MathML3 DTD is retained for compatibility:

```text
backend/schemas/JATS-Publishing-1-4-MathML3-DTD/
```

`JatsSchemaValidator` chooses the matching local DTD from the XML `dtd-version` attribute. You may still override discovery with `JATS_SCHEMA_PATH` when testing another local RNG, XSD, or DTD.

Keep every `.dtd`, `.ent`, `.mod`, and supporting subdirectory together because the main DTD loads modules through relative paths.
