from typing import Any

from lxml import etree

from app.utils.xml_utils import parse_untrusted_xml


class OmmlConverter:
    """Convert a maintainable subset of OMML to Presentation MathML and LaTeX."""

    OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    MATHML_NS = "http://www.w3.org/1998/Math/MathML"
    NS = {"m": OMML_NS}
    PROPERTY_NODES = {
        "ctrlPr", "dPr", "fPr", "naryPr", "radPr", "sSubPr", "sSupPr", "sSubSupPr",
        "mPr", "mrPr", "eqArrPr", "accPr",
    }
    CONTAINER_NODES = {"oMath", "oMathPara", "e", "num", "den", "sup", "sub", "deg"}
    OPERATORS = set("+-=≈≤≥×÷∑∫√()[]{}|,")
    LATEX_OPERATORS = {"∑": r"\sum", "∫": r"\int", "√": r"\sqrt"}

    ACCENTS = {
        "^": ("^", r"\hat", "accent_hat"),
        "ˆ": ("^", r"\hat", "accent_hat"),
        "¯": ("¯", r"\bar", "accent_bar"),
        "̅": ("¯", r"\bar", "accent_bar"),
        "˙": ("˙", r"\dot", "accent_dot"),
        ".": ("˙", r"\dot", "accent_dot"),
        "~": ("~", r"\tilde", "accent_tilde"),
        "˜": ("~", r"\tilde", "accent_tilde"),
    }

    def convert(self, omml: str) -> dict[str, Any]:
        self.supported_features: set[str] = set()
        self.unsupported_features: set[str] = set()
        self.issues: list[dict[str, str]] = []
        try:
            root = parse_untrusted_xml(omml)
            math = etree.Element(
                f"{{{self.MATHML_NS}}}math", nsmap={"mml": self.MATHML_NS}
            )
            converted = self._to_mathml(root)
            if converted is None or not self._has_content(converted):
                return self._result("", "", "failed")
            if self._local(converted) == "mrow":
                for child in list(converted):
                    math.append(child)
            else:
                math.append(converted)
            status = "partial" if self.unsupported_features else "success"
            return self._result(
                etree.tostring(math, encoding="unicode"),
                self._to_latex(root).strip(),
                status,
            )
        except (etree.XMLSyntaxError, ValueError, TypeError):
            self._unsupported("invalid_omml", "OMML 无法解析，需人工复核。")
            return self._result("", "", "failed")

    def _to_mathml(self, node: Any) -> Any | None:
        name = self._local(node)
        if name in self.PROPERTY_NODES:
            return None
        if name in self.CONTAINER_NODES:
            return self._row(node)
        if name in {"r", "t"}:
            return self._token("".join(node.xpath(".//m:t/text() | self::m:t/text()", namespaces=self.NS)))
        if name == "f":
            self.supported_features.add("fraction")
            return self._binary("mfrac", self._child(node, "num"), self._child(node, "den"))
        if name == "sSup":
            self.supported_features.add("superscript")
            return self._binary("msup", self._child(node, "e"), self._child(node, "sup"))
        if name == "sSub":
            self.supported_features.add("subscript")
            return self._binary("msub", self._child(node, "e"), self._child(node, "sub"))
        if name == "sSubSup":
            self.supported_features.add("subsup")
            element = self._math_element("msubsup")
            for child_name in ("e", "sub", "sup"):
                element.append(self._converted_or_row(self._child(node, child_name)))
            return element
        if name == "rad":
            self.supported_features.add("radical")
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
            self.supported_features.add("nary_limits")
            return self._nary_mathml(node)
        if name == "m":
            self.supported_features.add("matrix")
            return self._table_mathml(node, "mr")
        if name == "eqArr":
            self.supported_features.add("equation_array")
            return self._table_mathml(node, "e")
        if name == "acc":
            return self._accent_mathml(node)
        if name == "d":
            begin = self._property_value(node, "begChr") or "("
            end = self._property_value(node, "endChr") or ")"
            eq_array = node.find(".//m:eqArr", self.NS)
            if begin == "{" and eq_array is not None:
                self.supported_features.update({"cases", "equation_array"})
                fenced = self._math_element("mfenced")
                fenced.set("open", "{")
                fenced.set("close", "")
                fenced.append(self._converted_or_row(eq_array))
                return fenced
            self.supported_features.add("delimiter")
            row = self._math_element("mrow")
            row.append(self._token(begin, force_operator=True))
            expression = self._to_mathml(self._child(node, "e"))
            if expression is not None:
                row.append(expression)
            row.append(self._token(end, force_operator=True))
            return row
        self._mark_unknown(node)
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
        if name == "m":
            return self._table_latex(node, "mr", "matrix")
        if name == "eqArr":
            return self._table_latex(node, "e", "aligned")
        if name == "acc":
            char = self._property_value(node, "chr")
            accent = self.ACCENTS.get(char)
            body = self._to_latex(self._child(node, "e"))
            return rf"{accent[1]}{{{body}}}" if accent else body
        if name == "d":
            begin = self._property_value(node, "begChr") or "("
            end = self._property_value(node, "endChr") or ")"
            eq_array = node.find(".//m:eqArr", self.NS)
            if begin == "{" and eq_array is not None:
                rows = [self._to_latex(child) for child in eq_array.findall("m:e", self.NS)]
                return r"\begin{cases}" + r" \\ ".join(rows) + r"\end{cases}"
            return f"{begin}{self._to_latex(self._child(node, 'e'))}{end}"
        return "".join(self._to_latex(child) for child in node if self._local(child) not in self.PROPERTY_NODES)

    def _row(self, node: Any) -> Any:
        row = self._math_element("mrow")
        for child in node:
            converted = self._to_mathml(child)
            if converted is not None:
                row.append(converted)
        return row

    def _table_mathml(self, node: Any, row_name: str) -> Any:
        table = self._math_element("mtable")
        rows = node.findall(f"m:{row_name}", self.NS)
        for row_node in rows:
            row = self._math_element("mtr")
            cells = row_node.findall("m:e", self.NS) if row_name == "mr" else [row_node]
            for cell_node in cells:
                cell = self._math_element("mtd")
                cell.append(self._converted_or_row(cell_node))
                row.append(cell)
            table.append(row)
        return table

    def _table_latex(self, node: Any, row_name: str, environment: str) -> str:
        rows = []
        for row_node in node.findall(f"m:{row_name}", self.NS):
            cells = row_node.findall("m:e", self.NS) if row_name == "mr" else [row_node]
            rows.append(" & ".join(self._to_latex(cell) for cell in cells))
        return rf"\begin{{{environment}}}" + r" \\ ".join(rows) + rf"\end{{{environment}}}"

    def _accent_mathml(self, node: Any) -> Any:
        char = self._property_value(node, "chr")
        accent = self.ACCENTS.get(char)
        body = self._converted_or_row(self._child(node, "e"))
        if accent is None:
            self._unsupported("complex_accent", f"无法识别重音符号 {char or '空'}，已保留主体内容。")
            return body
        self.supported_features.add(accent[2])
        mover = self._math_element("mover")
        mover.set("accent", "true")
        mover.append(body)
        mover.append(self._token(accent[0], force_operator=True))
        return mover

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

    def _mark_unknown(self, node: Any) -> None:
        name = self._local(node)
        if etree.QName(node).namespace == self.OMML_NS and name not in {"r", "t"}:
            self._unsupported(f"omml_{name}", f"OMML 子结构 {name} 尚未完整支持，已保留可识别内容。")

    def _unsupported(self, feature: str, message: str) -> None:
        self.unsupported_features.add(feature)
        issue = {"level": "warning", "message": message, "suggestion": "请人工复核公式 MathML 与 LaTeX。"}
        if issue not in self.issues:
            self.issues.append(issue)

    def _result(self, mathml: str, latex: str, status: str) -> dict[str, Any]:
        return {
            "mathml": mathml,
            "latex": latex,
            "conversion_status": status,
            "supported_features": sorted(self.supported_features),
            "unsupported_features": sorted(self.unsupported_features),
            "issues": list(self.issues),
        }

    @staticmethod
    def _local(node: Any) -> str:
        return etree.QName(node).localname

    @staticmethod
    def _text(node: Any) -> str:
        return "".join(node.itertext()).strip()

    @staticmethod
    def _has_content(node: Any) -> bool:
        return bool(len(node) or (node.text and node.text.strip()))
