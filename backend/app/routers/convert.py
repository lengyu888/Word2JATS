import mimetypes
import re
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
from app.services.flow_view_builder import FlowViewBuilder
from app.services.jats_generator import JatsGenerator
from app.services.jats_auto_fixer import JatsAutoFixer
from app.services.package_exporter import PackageExporter
from app.services.profile_loader import ProfileLoader
from app.services.quality_scorer import QualityScorer
from app.services.validator import ArticleValidator
from app.services.visual_preview_builder import VisualPreviewBuilder
from app.utils.file_utils import safe_filename, save_upload


router = APIRouter(prefix="/api", tags=["conversion"])
TEMP_ROOT = Path(__file__).resolve().parents[2] / "temp"
package_exporter = PackageExporter(TEMP_ROOT)
profile_loader = ProfileLoader()
quality_scorer = QualityScorer()
flow_view_builder = FlowViewBuilder()
visual_preview_builder = VisualPreviewBuilder()
SAMPLE_ROOT = Path(__file__).resolve().parents[3] / "sample_documents"
CONVERSION_ID_RE = re.compile(r"^[a-f0-9]{32}$")
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _generate_outputs(article: dict, profile: dict) -> tuple[str, dict, dict]:
    xml = JatsGenerator(profile).generate(article)
    validator = ArticleValidator()
    initial_schema = validator.schema_validator.validate(xml)
    xml, auto_fix, final_schema = JatsAutoFixer(validator.schema_validator).fix(
        xml, initial_schema
    )
    validation = validator.validate(
        article, xml, schema_result=final_schema, auto_fix=auto_fix
    )
    quality_report = quality_scorer.score(article, validation)
    return xml, validation, quality_report


async def _convert_upload(file: UploadFile, profile_name: str = "default") -> dict:
    if not file.filename or Path(file.filename).suffix.lower() != ".docx":
        raise ValueError("仅支持 .docx 文件。")
    work_dir = TEMP_ROOT / uuid4().hex
    source = await save_upload(file, work_dir / safe_filename(file.filename))
    try:
        profile = profile_loader.load(profile_name)
        parser = DocxParser(source, work_dir / "media", profile)
        article = parser.parse()
    finally:
        source.unlink(missing_ok=True)
    xml, validation, quality_report = _generate_outputs(article, profile)
    visual_preview_builder.enrich(article, work_dir.name, quality_report)
    article["document_flow_view"] = flow_view_builder.build(
        article, parser.document_flow_nodes, validation, quality_report
    )
    media_paths = [
        figure.get("path", "")
        for figure in article.get("figures", [])
        if figure.get("path")
    ]
    return {
        "success": True,
        "conversion_id": work_dir.name,
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
    xml, validation, quality_report = _generate_outputs(article, profile)
    visual_preview_builder.enrich(article, "", quality_report)
    article["document_flow_view"] = flow_view_builder.build(
        article, [], validation, quality_report
    )
    return {
        "success": True,
        "article": article,
        "xml": xml,
        "validation": validation,
        "quality_report": quality_report,
    }


@router.get("/profiles")
def list_profiles() -> dict:
    return {"profiles": profile_loader.list_profiles()}


@router.get("/media/{conversion_id}/{filename}")
def read_media(conversion_id: str, filename: str) -> FileResponse:
    if not CONVERSION_ID_RE.fullmatch(conversion_id):
        raise HTTPException(status_code=400, detail="无效的 conversion_id。")
    if filename != Path(filename).name or safe_filename(filename) != filename:
        raise HTTPException(status_code=400, detail="无效的媒体文件名。")
    if Path(filename).suffix.lower() not in MEDIA_EXTENSIONS:
        raise HTTPException(status_code=404, detail="不支持的媒体文件格式。")
    media_dir = (TEMP_ROOT / conversion_id / "media").resolve()
    path = (media_dir / filename).resolve()
    if not path.is_relative_to(media_dir) or not path.is_file():
        raise HTTPException(status_code=404, detail="媒体文件不存在。")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.get("/demo-document")
def demo_document() -> FileResponse:
    path = SAMPLE_ROOT / "word2jats_final_acceptance.docx"
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
