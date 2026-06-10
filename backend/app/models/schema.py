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


class ArticleTable(BaseModel):
    id: str
    caption: str = ""
    rows: list[list[str]] = Field(default_factory=list)
    section_index: int = -1


class ArticleList(BaseModel):
    id: str
    items: list[str] = Field(default_factory=list)
    section_index: int = -1


class Formula(BaseModel):
    id: str = ""
    content: str = ""
    type: str = "plain_text"
    section_index: int = -1

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_formula(cls, value):
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.setdefault("content", normalized.get("tex") or normalized.get("plain_text") or "")
        normalized.setdefault("type", "plain_text")
        return normalized


class Reference(BaseModel):
    id: str = ""
    label: str = ""
    raw: str = ""

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
        return normalized


class Article(BaseModel):
    title: str = ""
    doi: str = ""
    article_type: str = "research-article"
    lang: str = "zh"
    journal_title: str = ""
    journal_id: str = ""
    publisher_name: str = ""
    subject: str = ""
    pub_year: str = ""
    pub_month: str = ""
    pub_day: str = ""
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


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ConvertResponse(BaseModel):
    success: bool
    article: Article
    xml: str
    validation: ValidationResult


class GenerateXmlRequest(BaseModel):
    article: Article


class GenerateXmlResponse(BaseModel):
    success: bool
    xml: str
    validation: ValidationResult
