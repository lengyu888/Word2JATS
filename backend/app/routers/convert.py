from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO

from app.models.schema import (
    BatchConvertResponse,
    ConvertResponse,
    ExportPackageRequest,
    GenerateXmlRequest,
    GenerateXmlResponse,
)
from app.services.docx_parser import DocxParser
from app.services.jats_generator import JatsGenerator
from app.services.package_exporter import PackageExporter
from app.services.profile_loader import ProfileLoader
from app.services.quality_scorer import QualityScorer
from app.services.validator import ArticleValidator
from app.utils.file_utils import safe_filename, save_upload


router = APIRouter(prefix="/api", tags=["conversion"])
TEMP_ROOT = Path(__file__).resolve().parents[2] / "temp"
package_exporter = PackageExporter(TEMP_ROOT)
profile_loader = ProfileLoader()
quality_scorer = QualityScorer()
SAMPLE_ROOT = Path(__file__).resolve().parents[3] / "sample_documents"


async def _convert_upload(file: UploadFile, profile_name: str = "default") -> dict:
    if not file.filename or Path(file.filename).suffix.lower() != ".docx":
        raise ValueError("仅支持 .docx 文件。")
    work_dir = TEMP_ROOT / uuid4().hex
    source = await save_upload(file, work_dir / safe_filename(file.filename))
    try:
        profile = profile_loader.load(profile_name)
        article = DocxParser(source, work_dir / "media", profile).parse()
    finally:
        source.unlink(missing_ok=True)
    xml = JatsGenerator(profile).generate(article)
    validation = ArticleValidator().validate(article, xml)
    quality_report = quality_scorer.score(article, validation)
    media_paths = [
        figure.get("path", "")
        for figure in article.get("figures", [])
        if figure.get("path")
    ]
    return {
        "success": True,
        "article": article,
        "xml": xml,
        "validation": validation,
        "quality_report": quality_report,
        "media_paths": media_paths,
    }


@router.post("/convert", response_model=ConvertResponse)
async def convert_docx(file: UploadFile = File(...), profile: str = Form("default")) -> dict:
    try:
        return await _convert_upload(file, profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"文档转换失败：{exc}") from exc


@router.post("/batch-convert", response_model=BatchConvertResponse)
async def batch_convert_docx(
    files: list[UploadFile] = File(...), profile: str = Form("default")
) -> dict:
    results = []
    for file in files:
        filename = file.filename or "unnamed.docx"
        try:
            converted = await _convert_upload(file, profile)
            results.append({
                "filename": filename,
                "status": "success",
                **converted,
            })
        except Exception as exc:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": str(exc),
            })
    return {
        "success": bool(results) and all(item["status"] == "success" for item in results),
        "results": results,
    }


@router.post("/generate-xml", response_model=GenerateXmlResponse)
def generate_xml(payload: GenerateXmlRequest) -> dict:
    article = payload.article.model_dump()
    profile = profile_loader.load(article.get("profile", "default"))
    article = ProfileLoader.apply_metadata(article, profile)
    xml = JatsGenerator(profile).generate(article)
    validation = ArticleValidator().validate(article, xml)
    quality_report = quality_scorer.score(article, validation)
    return {
        "success": True,
        "xml": xml,
        "validation": validation,
        "quality_report": quality_report,
    }


@router.get("/profiles")
def list_profiles() -> dict:
    return {"profiles": profile_loader.list_profiles()}


@router.get("/demo-document")
def demo_document() -> FileResponse:
    path = SAMPLE_ROOT / "word2jats_feature_acceptance.docx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Demo document is not available.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name,
    )


@router.post("/export-package")
def export_package(payload: ExportPackageRequest) -> StreamingResponse:
    try:
        content = package_exporter.build(
            filename=payload.filename,
            article=payload.article.model_dump(),
            xml=payload.xml,
            media_paths=payload.media_paths,
            validation=payload.validation.model_dump(),
            quality_report=payload.quality_report.model_dump() if payload.quality_report else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    package_name = f"{Path(safe_filename(payload.filename)).stem or 'article'}-word2jats.zip"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{package_name}"'},
    )
