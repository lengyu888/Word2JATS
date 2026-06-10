from typing import Any

from lxml import etree


class OmmlConverter:
    """Convert a maintainable subset of OMML to Presentation MathML and LaTeX."""

    OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    MATHML_NS = "http://www.w3.org/1998/Math/MathML"
    NS = {"m": OMML_NS}
    PROPERTY_NODES = {
        "ctrlPr", "dPr", "fPr", "naryPr", "radPr", "sSubPr", "sSupPr", "sSubSupPr",
    }
    OPERATORS = set("+-=≈≤≥×÷∑∫√()[]{}|,")
    LATEX_OPERATORS = {"∑": r"\sum", "∫": r"\int", "√": r"\sqrt"}

    def convert(self, omml: str) -> dict[str, str]:
        try:
            root = etree.fromstring(omml.encode("utf-8"))
            math = etree.Element(
                f"{{{self.MATHML_NS}}}math", nsmap={"mml": self.MATHML_NS}
            )
            converted = self._to_mathml(root)
            if converted is None or not self._has_content(converted):
                return {"mathml": "", "latex": ""}
            if self._local(converted) == "mrow":
                for child in list(converted):
                    math.append(child)
            else:
                math.append(converted)
            return {
                "mathml": etree.tostring(math, encoding="unicode"),
                "latex": self._to_latex(root).strip(),
            }
        except (etree.XMLSyntaxError, ValueError, TypeError):
            return {"mathml": "", "latex": ""}

    def _to_mathml(self, node: Any) -> Any | None:
        name = self._local(node)
        if name in self.PROPERTY_NODES:
            return None
        if name in {"oMath", "oMathPara", "e", "num", "den", "sup", "sub", "deg"}:
            return self._row(node)
        if name in {"r", "t"}:
            return self._token("".join(node.xpath(".//m:t/text() | self::m:t/text()", namespaces=self.NS)))
        if name == "f":
            return self._binary("mfrac", self._child(node, "num"), self._child(node, "den"))
        if name == "sSup":
            return self._binary("msup", self._child(node, "e"), self._child(node, "sup"))
        if name == "sSub":
            return self._binary("msub", self._child(node, "e"), self._child(node, "sub"))
        if name == "sSubSup":
            element = self._math_element("msubsup")
            for child_name in ("e", "sub", "sup"):
                element.append(self._converted_or_row(self._child(node, child_name)))
            return element
        if name == "rad":
            degree = self._child(node, "deg")
            expression = self._converted_or_row(self._child(node, "e"))
            if degree is not None and self._text(degree):
                element = self._math_element("mroot")
                element.append(expression)
                element.append(self._converted_or_row(degree))
                return element
            element = self._math_element("msqrt")
            element.append(expression)
            return element
        if name == "nary":
            return self._nary_mathml(node)
        if name == "d":
            begin = self._property_value(node, "begChr") or "("
            end = self._property_value(node, "endChr") or ")"
            row = self._math_element("mrow")
            row.append(self._token(begin, force_operator=True))
            expression = self._to_mathml(self._child(node, "e"))
            if expression is not None:
                row.append(expression)
            row.append(self._token(end, force_operator=True))
            return row
        return self._row(node)

    def _nary_mathml(self, node: Any) -> Any:
        operator = self._property_value(node, "chr") or "∑"
        base = self._token(operator, force_operator=True)
        lower = self._child(node, "sub")
        upper = self._child(node, "sup")
        if lower is not None and upper is not None:
            limits = self._math_element("munderover")
            limits.append(base)
            limits.append(self._converted_or_row(lower))
            limits.append(self._converted_or_row(upper))
        elif lower is not None:
            limits = self._math_element("munder")
            limits.append(base)
            limits.append(self._converted_or_row(lower))
        elif upper is not None:
            limits = self._math_element("mover")
            limits.append(base)
            limits.append(self._converted_or_row(upper))
        else:
            limits = base
        row = self._math_element("mrow")
        row.append(limits)
        expression = self._to_mathml(self._child(node, "e"))
        if expression is not None:
            row.append(expression)
        return row

    def _to_latex(self, node: Any | None) -> str:
        if node is None:
            return ""
        name = self._local(node)
        if name in self.PROPERTY_NODES:
            return ""
        if name in {"r", "t"}:
            return "".join(node.xpath(".//m:t/text() | self::m:t/text()", namespaces=self.NS))
        if name == "f":
            return rf"\frac{{{self._to_latex(self._child(node, 'num'))}}}{{{self._to_latex(self._child(node, 'den'))}}}"
        if name == "sSup":
            return rf"{self._group_latex(self._child(node, 'e'))}^{{{self._to_latex(self._child(node, 'sup'))}}}"
        if name == "sSub":
            return rf"{self._group_latex(self._child(node, 'e'))}_{{{self._to_latex(self._child(node, 'sub'))}}}"
        if name == "sSubSup":
            return (
                rf"{self._group_latex(self._child(node, 'e'))}"
                rf"_{{{self._to_latex(self._child(node, 'sub'))}}}"
                rf"^{{{self._to_latex(self._child(node, 'sup'))}}}"
            )
        if name == "rad":
            degree = self._to_latex(self._child(node, "deg"))
            expression = self._to_latex(self._child(node, "e"))
            return rf"\sqrt[{degree}]{{{expression}}}" if degree else rf"\sqrt{{{expression}}}"
        if name == "nary":
            operator = self.LATEX_OPERATORS.get(self._property_value(node, "chr") or "∑", r"\sum")
            lower = self._to_latex(self._child(node, "sub"))
            upper = self._to_latex(self._child(node, "sup"))
            limits = (rf"_{{{lower}}}" if lower else "") + (rf"^{{{upper}}}" if upper else "")
            return f"{operator}{limits}{self._group_latex(self._child(node, 'e'))}"
        if name == "d":
            begin = self._property_value(node, "begChr") or "("
            end = self._property_value(node, "endChr") or ")"
            return f"{begin}{self._to_latex(self._child(node, 'e'))}{end}"
        return "".join(self._to_latex(child) for child in node if self._local(child) not in self.PROPERTY_NODES)

    def _row(self, node: Any) -> Any:
        row = self._math_element("mrow")
        for child in node:
            converted = self._to_mathml(child)
            if converted is not None:
                row.append(converted)
        return row

    def _binary(self, name: str, first: Any | None, second: Any | None) -> Any:
        element = self._math_element(name)
        element.append(self._converted_or_row(first))
        element.append(self._converted_or_row(second))
        return element

    def _converted_or_row(self, node: Any | None) -> Any:
        converted = self._to_mathml(node) if node is not None else None
        return converted if converted is not None else self._math_element("mrow")

    def _token(self, text: str, force_operator: bool = False) -> Any:
        text = text.strip()
        tag = "mo" if force_operator or text in self.OPERATORS else ("mn" if text.isdigit() else "mi")
        element = self._math_element(tag)
        element.text = text
        return element

    def _group_latex(self, node: Any | None) -> str:
        value = self._to_latex(node)
        return value if len(value) <= 1 else f"{{{value}}}"

    def _child(self, node: Any, name: str) -> Any | None:
        return node.find(f"m:{name}", self.NS)

    def _property_value(self, node: Any, name: str) -> str:
        values = node.xpath(f".//m:{name}/@m:val", namespaces=self.NS)
        return values[0] if values else ""

    def _math_element(self, name: str) -> Any:
        return etree.Element(f"{{{self.MATHML_NS}}}{name}")

    @staticmethod
    def _local(node: Any) -> str:
        return etree.QName(node).localname

    @staticmethod
    def _text(node: Any) -> str:
        return "".join(node.itertext()).strip()

    @staticmethod
    def _has_content(node: Any) -> bool:
        return bool(len(node) or (node.text and node.text.strip()))
