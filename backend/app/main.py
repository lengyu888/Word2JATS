from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.security import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from app.routers.convert import router as convert_router
from app.services.document_security import DocumentSecurityPolicy


app = FastAPI(
    title="Word2JATS API",
    description="面向学术出版的 Word 文档智能结构化转换服务",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security_policy = DocumentSecurityPolicy.from_env()
app.add_middleware(
    RequestBodyLimitMiddleware, max_body_bytes=security_policy.max_request_bytes
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(convert_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
