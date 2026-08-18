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
            root = etree.fromstring(
                xml.encode("utf-8"),
                etree.XMLParser(
                    no_network=True,
                    resolve_entities=False,
                    load_dtd=False,
                    huge_tree=False,
                ),
            )
            result["xml_well_formed"] = True
        except (etree.XMLSyntaxError, ValueError) as exc:
            result["schema_errors"].append(f"XML is not well formed: {exc}")
            return result

        schema_path = self._find_schema(root.get("dtd-version") or "1.3")
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

    def _find_schema(self, dtd_version: str = "1.3") -> Path | None:
        configured = os.getenv("JATS_SCHEMA_PATH")
        if configured:
            path = Path(configured)
            if path.exists():
                return path
        if not self.schema_dir.exists():
            return None

        version_key = self._normalize_version(dtd_version)
        preferred_names = {
            "1.3": (
                "JATS-journalpublishing1-3-mathml3.dtd",
                "JATS-journalpublishing1-3.dtd",
            ),
            "1.4": (
                "JATS-journalpublishing1-4-mathml3.dtd",
                "JATS-journalpublishing1-4.dtd",
            ),
        }.get(version_key, ())
        files = [
            path for path in self.schema_dir.rglob("*")
            if path.is_file() and "__MACOSX" not in path.parts and not path.name.startswith("._")
        ]
        for name in preferred_names:
            matches = sorted(path for path in files if path.name == name)
            if matches:
                return matches[0]

        for suffix in ("*.rng", "*.xsd", "*.dtd"):
            candidates = sorted(
                path for path in self.schema_dir.rglob(suffix)
                if "__MACOSX" not in path.parts and not path.name.startswith("._")
            )
            if candidates:
                versioned = [
                    path for path in candidates
                    if version_key.replace(".", "-") in str(path).lower()
                    or version_key in str(path).lower()
                ]
                preferred = [
                    path for path in (versioned or candidates)
                    if "publishing" in path.name.lower() or "jats" in path.name.lower()
                ]
                return (preferred or versioned or candidates)[0]
        return None

    @staticmethod
    def _normalize_version(value: str) -> str:
        if str(value).startswith("1.4"):
            return "1.4"
        return "1.3"

    @staticmethod
    def _load_validator(path: Path):
        parser = etree.XMLParser(no_network=True, resolve_entities=False)
        if path.suffix.lower() == ".rng":
            return etree.RelaxNG(etree.parse(str(path), parser))
        if path.suffix.lower() == ".xsd":
            return etree.XMLSchema(etree.parse(str(path), parser))
        return etree.DTD(str(path))
