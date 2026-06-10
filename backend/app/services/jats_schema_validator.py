import os
from pathlib import Path
from typing import Any

from lxml import etree


class JatsSchemaValidator:
    """Validate XML against a locally installed RNG, XSD, or DTD schema."""

    def __init__(self, schema_dir: str | Path | None = None):
        self.schema_dir = Path(schema_dir or Path(__file__).resolve().parents[2] / "schemas")

    def validate(self, xml: str) -> dict[str, Any]:
        result = {
            "xml_well_formed": False,
            "jats_schema_valid": None,
            "schema_errors": [],
            "schema_file": "",
        }
        try:
            root = etree.fromstring(xml.encode("utf-8"), etree.XMLParser(no_network=True))
            result["xml_well_formed"] = True
        except (etree.XMLSyntaxError, ValueError) as exc:
            result["schema_errors"].append(f"XML is not well formed: {exc}")
            return result

        schema_path = self._find_schema()
        if not schema_path:
            result["schema_errors"].append(
                "Official JATS schema is not configured. Place a local RNG, XSD, or DTD in backend/schemas/."
            )
            return result

        result["schema_file"] = schema_path.name
        try:
            validator = self._load_validator(schema_path)
            result["jats_schema_valid"] = bool(validator.validate(root))
            if not result["jats_schema_valid"]:
                result["schema_errors"].extend(str(item) for item in validator.error_log)
        except (OSError, etree.XMLSyntaxError, etree.RelaxNGParseError, etree.XMLSchemaParseError) as exc:
            result["jats_schema_valid"] = False
            result["schema_errors"].append(f"Unable to load JATS schema {schema_path.name}: {exc}")
        return result

    def _find_schema(self) -> Path | None:
        configured = os.getenv("JATS_SCHEMA_PATH")
        if configured:
            path = Path(configured)
            if path.exists():
                return path
        if not self.schema_dir.exists():
            return None
        for suffix in ("*.rng", "*.xsd", "*.dtd"):
            candidates = sorted(self.schema_dir.rglob(suffix))
            if candidates:
                preferred = [
                    path for path in candidates
                    if "publishing" in path.name.lower() or "jats" in path.name.lower()
                ]
                return (preferred or candidates)[0]
        return None

    @staticmethod
    def _load_validator(path: Path):
        parser = etree.XMLParser(no_network=True, resolve_entities=False)
        if path.suffix.lower() == ".rng":
            return etree.RelaxNG(etree.parse(str(path), parser))
        if path.suffix.lower() == ".xsd":
            return etree.XMLSchema(etree.parse(str(path), parser))
        return etree.DTD(str(path))
