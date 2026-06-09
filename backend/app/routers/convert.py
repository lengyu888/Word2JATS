from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schema import ConvertResponse, GenerateXmlRequest, GenerateXmlResponse
from app.services.docx_parser import DocxParser
from app.services.jats_generator import JatsGenerator
from app.services.validator import ArticleValidator
from app.utils.file_utils import safe_filename, save_upload


router = APIRouter(prefix="/api", tags=["conversion"])
TEMP_ROOT = Path(__file__).resolve().parents[2] / "temp"


@router.post("/convert", response_model=ConvertResponse)
async def convert_docx(file: UploadFile = File(...)) -> dict:
    if not file.filename or Path(file.filename).suffix.lower() != ".docx":
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件。")
    try:
        work_dir = TEMP_ROOT / uuid4().hex
        source = await save_upload(file, work_dir / safe_filename(file.filename))
        article = DocxParser(source, work_dir / "media").parse()
        source.unlink(missing_ok=True)
        xml = JatsGenerator().generate(article)
        validation = ArticleValidator().validate(article, xml)
        return {
            "success": True,
            "article": article,
            "xml": xml,
            "validation": validation,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"文档转换失败：{exc}") from exc


@router.post("/generate-xml", response_model=GenerateXmlResponse)
def generate_xml(payload: GenerateXmlRequest) -> dict:
    article = payload.article.model_dump()
    xml = JatsGenerator().generate(article)
    validation = ArticleValidator().validate(article, xml)
    return {"success": True, "xml": xml, "validation": validation}
