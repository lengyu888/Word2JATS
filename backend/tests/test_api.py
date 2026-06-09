from fastapi.testclient import TestClient

from app.main import app
from tests.test_services import build_sample_docx


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_convert_endpoint_returns_all_outputs():
    response = client.post(
        "/api/convert",
        files={
            "file": (
                "sample.docx",
                build_sample_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["article"]["title"] == "面向出版的智能结构化转换"
    assert payload["xml"].startswith("<?xml")
    assert payload["validation"]["passed"] is True


def test_convert_endpoint_rejects_non_docx():
    response = client.post(
        "/api/convert",
        files={"file": ("paper.txt", b"not a docx", "text/plain")},
    )

    assert response.status_code == 400


def test_generate_xml_endpoint_uses_corrected_article():
    response = client.post(
        "/api/generate-xml",
        json={
            "article": {
                "title": "人工校正后的标题",
                "authors": [{"name": "张三", "orcid": ""}],
                "affiliations": ["校正大学"],
                "abstract": "人工校正后的摘要",
                "keywords": ["校正", "JATS"],
                "sections": [
                    {
                        "title": "校正后的章节",
                        "level": 1,
                        "paragraphs": ["校正后的正文段落。"],
                    }
                ],
                "figures": [],
                "lists": [],
                "formulas": [],
                "references": [{"raw": "[1] 校正后的参考文献"}],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert "<article-title>人工校正后的标题</article-title>" in payload["xml"]
    assert "<title>校正后的章节</title>" in payload["xml"]
    assert payload["validation"]["passed"] is True


def test_generate_xml_endpoint_normalizes_missing_optional_collections():
    response = client.post(
        "/api/generate-xml",
        json={
            "article": {
                "title": "最小文章",
                "abstract": "摘要",
                "keywords": ["关键词"],
                "sections": [{"title": "引言", "paragraphs": ["正文"]}],
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["validation"]["passed"] is True


def test_generate_xml_endpoint_accepts_legacy_formula_fields():
    response = client.post(
        "/api/generate-xml",
        json={
            "article": {
                "title": "公式兼容测试",
                "abstract": "摘要",
                "keywords": ["公式", "JATS", "测试"],
                "sections": [{"title": "方法", "paragraphs": ["正文"]}],
                "formulas": [{"plain_text": "E = mc²", "section_index": 0}],
            }
        },
    )

    assert response.status_code == 200
    assert '<disp-formula id="eq1">' in response.json()["xml"]
    assert "<![CDATA[E = mc²]]>" in response.json()["xml"]
