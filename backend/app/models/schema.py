import re

from pydantic import BaseModel, Field, model_validator


class Author(BaseModel):
    name: str
    orcid: str = ""
    affiliation_ids: list[str] = Field(default_factory=list)


class Section(BaseModel):
    title: str
    level: int = 1
    paragraphs: list[str] = Field(default_factory=list)


class Figure(BaseModel):
    id: str
    caption: str = ""
    path: str = ""
    section_index: int = -1
    filename: str = ""
    media_url: str = ""
    section_id: str = ""
    section_title: str = ""
    referenced_by: list[str] = Field(default_factory=list)
    status: str = "ok"
    issues: list["FlowViewIssue"] = Field(default_factory=list)


class ArticleTable(BaseModel):
    id: str
    caption: str = ""
    rows: list[list[str]] = Field(default_factory=list)
    section_index: int = -1
    section_id: str = ""
    section_title: str = ""
    referenced_by: list[str] = Field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    status: str = "ok"
    issues: list["FlowViewIssue"] = Field(default_factory=list)


class ArticleList(BaseModel):
    id: str
    items: list[str] = Field(default_factory=list)
    section_index: int = -1


class Formula(BaseModel):
    id: str = ""
    content: str = ""
    omml: str = ""
    mathml: str = ""
    latex: str = ""
    type: str = "plain_text"
    section_index: int = -1
    conversion_status: str = "success"
    supported_features: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_formula(cls, value):
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.setdefault(
            "content",
            normalized.get("latex") or normalized.get("tex") or normalized.get("plain_text") or "",
        )
        normalized.setdefault("latex", normalized.get("tex") or "")
        normalized.setdefault("type", "plain_text")
        normalized.setdefault(
            "conversion_status",
            "failed" if normalized.get("type") == "omml" and not normalized.get("mathml") else "success",
        )
        return normalized


class Reference(BaseModel):
    id: str = ""
    label: str = ""
    raw: str = ""
    mixed_citation: str = ""
    authors: list[str] = Field(default_factory=list)
    article_title: str = ""
    source: str = ""
    year: str = ""
    volume: str = ""
    issue: str = ""
    fpage: str = ""
    lpage: str = ""
    doi: str = ""
    publication_type: str = ""
    parse_confidence: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_reference(cls, value):
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        raw = normalized.get("raw", "")
        if not normalized.get("label") and isinstance(raw, str):
            match = re.match(
                r"^\s*(\[\s*\d+\s*\]|\(\s*\d+\s*\)|（\s*\d+\s*）|\d+\s*[.．、])\s*(.*)$",
                raw,
            )
            if match:
                normalized["label"] = match.group(1).strip()
                normalized["raw"] = match.group(2).strip()
        normalized.setdefault("mixed_citation", normalized.get("raw", ""))
        return normalized


class FlowViewIssue(BaseModel):
    level: str = "warning"
    message: str = ""
    suggestion: str = ""


class FlowViewSource(BaseModel):
    paragraph_index: int | None = None
    table_index: int | None = None
    media_name: str | None = None


class FlowViewNode(BaseModel):
    index: int
    node_type: str
    text: str = ""
    preview: str = ""
    section_id: str = ""
    section_title: str = ""
    jats_path: str = ""
    jats_tag: str = "unknown"
    target_id: str | None = None
    confidence: float = 0.0
    status: str = "need_review"
    issues: list[FlowViewIssue] = Field(default_factory=list)
    source: FlowViewSource = Field(default_factory=FlowViewSource)


class Article(BaseModel):
    title: str = ""
    doi: str = ""
    article_type: str = "research-article"
    lang: str = "zh"
    journal_title: str = ""
    journal_id: str = ""
    issn: str = ""
    publisher_name: str = ""
    subject: str = ""
    pub_year: str = ""
    pub_month: str = ""
    pub_day: str = ""
    profile: str = "default"
    authors: list[Author] = Field(default_factory=list)
    affiliations: list[str] = Field(default_factory=list)
    abstract: str = ""
    keywords: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    tables: list[ArticleTable] = Field(default_factory=list)
    lists: list[ArticleList] = Field(default_factory=list)
    formulas: list[Formula] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    document_flow_view: list[FlowViewNode] = Field(default_factory=list)


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    schema_errors: list[str] = Field(default_factory=list)
    xref_checks: list[str] = Field(default_factory=list)
    xml_well_formed: bool = False
    jats_schema_valid: bool | None = None
    schema_file: str = ""
    business_rules: dict = Field(default_factory=dict)
    auto_fix: dict = Field(default_factory=dict)

class QualityIssue(BaseModel):
    level: str
    module: str
    location: str
    message: str
    suggestion: str


class QualityReport(BaseModel):
    total_score: int
    grade: str
    scores: dict[str, int] = Field(default_factory=dict)
    issues: list[QualityIssue] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
    formula_summary: dict = Field(default_factory=dict)


class ConvertResponse(BaseModel):
    success: bool
    conversion_id: str
    article: Article
    xml: str
    validation: ValidationResult
    quality_report: QualityReport | None = None
    media_paths: list[str] = Field(default_factory=list)
    official_comparison: dict = Field(default_factory=dict)


class GenerateXmlRequest(BaseModel):
    article: Article


class GenerateXmlResponse(BaseModel):
    success: bool
    article: Article
    xml: str
    validation: ValidationResult
    quality_report: QualityReport | None = None


class BatchConvertItem(BaseModel):
    filename: str
    status: str
    conversion_id: str = ""
    article: Article | None = None
    xml: str = ""
    validation: ValidationResult | None = None
    quality_report: QualityReport | None = None
    media_paths: list[str] = Field(default_factory=list)
    official_comparison: dict = Field(default_factory=dict)
    error: str = ""


class BatchConvertResponse(BaseModel):
    success: bool
    results: list[BatchConvertItem] = Field(default_factory=list)


class ExportPackageRequest(BaseModel):
    filename: str = "article.docx"
    article: Article
    xml: str
    media_paths: list[str] = Field(default_factory=list)
    validation: ValidationResult
    quality_report: QualityReport | None = None
