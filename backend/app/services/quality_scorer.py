from typing import Any


class QualityScorer:
    WEIGHTS = {
        "metadata_score": 20,
        "structure_score": 15,
        "jats_schema_score": 20,
        "figure_table_score": 10,
        "formula_score": 10,
        "reference_score": 15,
        "xref_score": 10,
    }

    def score(self, article: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        scores = {
            "metadata_score": self._metadata(article, issues),
            "structure_score": self._structure(article, issues),
            "jats_schema_score": self._schema(validation, issues),
            "figure_table_score": self._figures_tables(article, issues),
            "formula_score": self._formulas(article, issues),
            "reference_score": self._references(article, issues),
            "xref_score": self._xrefs(validation, issues),
        }
        self._validation_issues(validation, issues)
        weighted = sum(scores[name] * weight for name, weight in self.WEIGHTS.items()) / 100
        total = round(weighted - min(30, len(validation.get("errors", [])) * 10))
        return {
            "total_score": max(0, min(100, total)),
            "grade": self._grade(total),
            "scores": scores,
            "issues": issues,
            "summary": {
                "error_count": sum(item["level"] == "error" for item in issues),
                "warning_count": sum(item["level"] == "warning" for item in issues),
                "suggestion_count": sum(item["level"] == "suggestion" for item in issues),
                "need_review_count": sum(item["level"] == "need_review" for item in issues),
            },
            "formula_summary": self._formula_summary(article),
        }

    def _metadata(self, article: dict[str, Any], issues: list[dict[str, str]]) -> int:
        fields = (
            ("title", "article.title", "补充文章标题"),
            ("abstract", "article.abstract", "补充摘要"),
            ("keywords", "article.keywords", "补充至少 3 个关键词"),
            ("authors", "article.authors", "补充作者信息"),
            ("affiliations", "article.affiliations", "补充作者单位"),
            ("journal_title", "article.journal_title", "通过 Profile 或人工校正补充期刊名"),
            ("publisher_name", "article.publisher_name", "补充出版者"),
        )
        present = 0
        for field, location, suggestion in fields:
            value = article.get(field)
            if value:
                present += 1
            else:
                self._issue(issues, "warning", "metadata", location, f"{field} 为空", suggestion)
        return round(present / len(fields) * 100)

    def _structure(self, article: dict[str, Any], issues: list[dict[str, str]]) -> int:
        sections = article.get("sections", [])
        if not sections:
            self._issue(issues, "error", "structure", "article.sections", "未识别到章节", "人工确认章节标题样式或调整 Profile")
            return 0
        empty = [index for index, section in enumerate(sections) if not section.get("paragraphs")]
        for index in empty:
            self._issue(issues, "warning", "structure", f"article.sections[{index}]", "章节没有正文段落", "检查章节边界或补充正文")
        return max(30, round((len(sections) - len(empty) * 0.5) / len(sections) * 100))

    def _schema(self, validation: dict[str, Any], issues: list[dict[str, str]]) -> int:
        if not validation.get("xml_well_formed"):
            self._issue(issues, "error", "jats_schema", "xml", "XML 无法解析", "修复 XML 语法后重新校验")
            return 0
        status = validation.get("jats_schema_valid")
        if status is True:
            return 100
        if status is None:
            self._issue(issues, "warning", "jats_schema", "backend/schemas", "未执行正式 JATS Schema 校验", "配置本地 JATS RNG/XSD/DTD")
            return 60
        for index, message in enumerate(validation.get("schema_errors", [])[:10]):
            self._issue(issues, "error", "jats_schema", f"schema_errors[{index}]", message, "根据正式 DTD 错误补齐或调整对应 JATS 节点")
        return max(10, 60 - min(50, len(validation.get("schema_errors", [])) * 10))

    def _figures_tables(self, article: dict[str, Any], issues: list[dict[str, str]]) -> int:
        items = [("figures", item, "图题", "caption") for item in article.get("figures", [])]
        items += [("tables", item, "表题", "caption") for item in article.get("tables", [])]
        if not items:
            return 100
        valid = 0
        for module, item, label, field in items:
            item_id = item.get("id", "unknown")
            if item.get(field) and (module != "tables" or item.get("rows")):
                valid += 1
            else:
                self._issue(issues, "warning", "figure_table", f"article.{module}.{item_id}", f"{item_id} 缺少{label}或内容", f"在人工校正页补充{label}并核对章节归属")
        return round(valid / len(items) * 100)

    def _formulas(self, article: dict[str, Any], issues: list[dict[str, str]]) -> int:
        formulas = article.get("formulas", [])
        if not formulas:
            return 100
        earned = 0.0
        for formula in formulas:
            formula_id = formula.get("id", "unknown")
            content = formula.get("mathml") or formula.get("latex") or formula.get("content")
            status = formula.get("conversion_status", "success" if content else "failed")
            if not content:
                self._issue(issues, "warning", "formula", f"article.formulas.{formula_id}", f"{formula_id} 没有可交付公式内容", "补充 MathML、LaTeX 或纯文本公式")
            if status == "success":
                earned += 1
            elif status == "partial":
                earned += 0.75
                unsupported = "、".join(formula.get("unsupported_features", [])) or "未知结构"
                self._issue(
                    issues, "need_review", "formula", f"article.formulas.{formula_id}",
                    f"{formula_id} 为部分转换，不支持特性：{unsupported}",
                    "人工复核 MathML 与 LaTeX，并按需校正公式",
                )
            else:
                earned += 0.25 if content else 0
                self._issue(
                    issues, "warning", "formula", f"article.formulas.{formula_id}",
                    f"{formula_id} 转换失败或仅保留回退内容",
                    "需要人工复核并补充 MathML 或 LaTeX",
                )
            if formula.get("type") == "omml" and not formula.get("mathml"):
                self._issue(issues, "suggestion", "formula", f"article.formulas.{formula_id}.mathml", f"{formula_id} 的 OMML 未转换为 MathML", "人工复核公式或扩展 OMML 转换规则")
        return round(earned / len(formulas) * 100)

    @staticmethod
    def _formula_summary(article: dict[str, Any]) -> dict[str, Any]:
        formulas = article.get("formulas", [])
        statuses = {"success": 0, "partial": 0, "failed": 0}
        unsupported = set()
        mathml_count = 0
        for formula in formulas:
            status = formula.get("conversion_status", "success")
            statuses[status if status in statuses else "failed"] += 1
            mathml_count += bool(formula.get("mathml"))
            unsupported.update(formula.get("unsupported_features", []))
        return {
            "total": len(formulas),
            "mathml_success": mathml_count,
            **statuses,
            "unsupported_features": sorted(unsupported),
        }

    def _references(self, article: dict[str, Any], issues: list[dict[str, str]]) -> int:
        references = article.get("references", [])
        if not references:
            self._issue(issues, "warning", "reference", "article.references", "没有参考文献", "补充参考文献并检查正文引用")
            return 40
        confidence = []
        for index, reference in enumerate(references):
            value = float(reference.get("parse_confidence") or 0)
            confidence.append(value)
            if value < 0.5:
                self._issue(issues, "suggestion", "reference", f"article.references[{index}]", "参考文献细粒度解析置信度较低", "人工校正作者、题名、来源、年份和 DOI")
        return round((sum(confidence) / len(confidence) if confidence else 0.4) * 100)

    def _xrefs(self, validation: dict[str, Any], issues: list[dict[str, str]]) -> int:
        unresolved = [
            warning for warning in validation.get("warnings", [])
            if "引用目标" in warning or "交叉引用" in warning
        ]
        for index, message in enumerate(unresolved):
            self._issue(issues, "warning", "xref", f"validation.xref_checks[{index}]", message, "检查正文引用编号与图表公式参考文献 ID")
        return max(0, 100 - len(unresolved) * 25)

    def _validation_issues(self, validation: dict[str, Any], issues: list[dict[str, str]]) -> None:
        existing_messages = {item["message"] for item in issues}
        for index, message in enumerate(validation.get("errors", [])):
            if message not in existing_messages:
                self._issue(
                    issues,
                    "error",
                    "business_rules",
                    f"validation.errors[{index}]",
                    message,
                    "根据校验错误修正对应文章字段或 JATS 节点",
                )
        for index, message in enumerate(validation.get("warnings", [])):
            if message not in existing_messages and "交叉引用" not in message:
                self._issue(
                    issues,
                    "warning",
                    "business_rules",
                    f"validation.warnings[{index}]",
                    message,
                    "在人工校正页复核并补充对应内容",
                )

    @staticmethod
    def _issue(issues, level, module, location, message, suggestion):
        issues.append({
            "level": level,
            "module": module,
            "location": location,
            "message": message,
            "suggestion": suggestion,
        })

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "E"
