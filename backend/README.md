# Word2JATS Backend

## 功能状态

| 能力 | 当前状态 |
| --- | --- |
| 本地 RNG/XSD/DTD 正式校验 | 已支持 |
| 官方 JATS Publishing 1.4 MathML3 DTD | 已内置 |
| 参考文献细粒度字段解析 | 已支持，复杂引文需人工复核 |
| Schema 白名单自动修复 | 已支持 |
| 图片公式 OCR、完整复杂 OMML | 尚未支持 |

## Profile 与正式 JATS Schema

`POST /api/convert` 和 `POST /api/batch-convert` 接受 multipart 字段 `profile`，可用值由 `GET /api/profiles` 返回。配置文件位于 `backend/profiles/*.yaml`，可定义期刊元数据、标题样式、摘要/关键词标记、图表题正则、参考文献风格和默认许可。

正式校验支持本地 RNG、XSD 或 DTD。仓库已在 `backend/schemas/` 内置官方 JATS Publishing 1.4 MathML3 DTD 完整发行包并自动发现主 DTD；如需切换其他本地 Schema，可设置 `JATS_SCHEMA_PATH` 指向主文件。未配置可用 Schema 时返回 `jats_schema_valid: null`，不会宣称正式合规。

为保持旧接口兼容，顶层 `passed` 表示 XML 合法且业务规则通过；正式 JATS 合规性必须单独查看 `jats_schema_valid` 与 `schema_errors`。

校验响应保持原有 `passed/errors/warnings/xref_checks`，并新增：

```json
{
  "xml_well_formed": true,
  "jats_schema_valid": null,
  "schema_errors": [],
  "schema_file": "",
  "business_rules": {"passed": true, "errors": [], "warnings": []},
  "auto_fix": {
    "attempted": true,
    "applied_fixes": [],
    "remaining_schema_errors": [],
    "before_schema_error_count": 0,
    "after_schema_error_count": 0
  }
}
```

`JatsAutoFixer` 根据首次 Schema 错误执行最多两轮白名单修复。目前支持将 `graphic/@href` 转换为 `xlink:href`、重新排列已知 `journal-meta` 子节点以及修复重复 XML ID。修复器不会补写 ISSN、DOI、ORCID 等无法可靠推断的真实数据。

参考文献解析器支持 GB/T 7714 与常见英文期刊启发式拆分。解析字段不完整时允许为空，并通过 `parse_confidence` 提示人工复核；生成器在结构化字段可用时输出 `element-citation`，否则回退 `mixed-citation`。

FastAPI 后端负责接收 Word 文档、执行规则解析、生成 JATS 风格 XML，并返回基础校验结果。服务无数据库、无商业 API 依赖，适合作为比赛原型和后续算法迭代基线。

## 技术栈

Python 3.10+、FastAPI、python-docx、lxml、Pydantic、pytest。

## 安装与启动

项目根目录一键启动：

```bash
docker compose up --build
```

请先启动 Docker Desktop（Linux containers）；前端入口为 `http://localhost:8080`。

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动后可访问：

- 健康检查：`GET http://127.0.0.1:8000/api/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- 转换接口：`POST http://127.0.0.1:8000/api/convert`
- 批量转换接口：`POST http://127.0.0.1:8000/api/batch-convert`
- 人工校正后生成 XML：`POST http://127.0.0.1:8000/api/generate-xml`
- ZIP 结果包导出：`POST http://127.0.0.1:8000/api/export-package`
- 内置演示稿下载：`GET http://127.0.0.1:8000/api/demo-document`

转换接口使用 `multipart/form-data`，字段名为 `file`，仅接受 `.docx`。

```bash
curl -F "file=@paper.docx" http://127.0.0.1:8000/api/convert
```

批量转换使用重复的 `files` 字段。每个文件独立返回 `status/article/xml/validation/media_paths/error`，单篇失败不会中断整个批次：

```bash
curl -F "files=@paper-1.docx" -F "files=@paper-2.docx" http://127.0.0.1:8000/api/batch-convert
```

`export-package` 接收单篇稿件的 `article`、`xml`、`media_paths` 和 `validation`，返回 ZIP 流。结果包包含：

```text
article.xml
article.json
validation_report.md
quality_report.json
manifest.json
media/
```

为避免路径逃逸，媒体文件只允许来自 `backend/temp` 转换目录。

`generate-xml` 接口接收经过人工校正的结构化文章：

```json
{
  "article": {
    "title": "校正后的标题",
    "abstract": "校正后的摘要",
    "keywords": ["JATS"],
    "sections": [{"title": "引言", "level": 1, "paragraphs": ["正文"]}]
  }
}
```

后端使用 Pydantic 统一补齐未提供的可选集合字段，再生成 XML 并返回最新校验结果。

Article 支持 DOI、文章类型、语言、期刊名称、期刊 ID、出版者、学科和出版日期等可选出版元数据。作者可通过 `affiliation_ids` 指定 `aff1`、`aff2` 等单位关联；未指定时默认关联全部单位。

## 处理流程

1. 将上传文件保存到请求级临时目录。
2. `DocumentFlowParser` 直接读取 `word/document.xml`，按 body 中 `w:p`、`w:tbl` 的真实顺序生成统一节点流，并通过 `document.xml.rels` 解析图片关系。
3. `OmmlConverter` 将常见 Word 原生公式结构转换为 Presentation MathML 和基础 LaTeX。
4. `DocxParser` 基于节点流提取元数据，并绑定章节、图片、图题、表格、表题、列表、OMML/规则公式和参考文献。
5. `XrefResolver` 识别正文中的图、表、公式和参考文献引用，`JatsGenerator` 使用 lxml 构建带混合内容 `xref` 的 XML。
6. `JatsGenerator` 生成 XML，并执行首次正式 JATS Schema 校验。
7. `JatsAutoFixer` 根据 Schema 错误执行安全修复并再次校验。
8. `ArticleValidator` 汇总业务规则、XML、最终 Schema 及交叉引用目标校验。
9. `QualityScorer` 生成 0-100 总分、七项分项得分和可定位修复建议。
10. 请求结束后清理临时文件。

## 测试

```bash
python -m pytest -q
```

测试覆盖核心解析规则、XML 生成、校验器、健康检查、转换接口、人工校正生成接口和错误文件类型。

`pytest.ini` 只收集 `tests/`，跳过 `backend/temp/`，将测试临时文件固定到项目根目录下按当前 Windows 用户隔离的 `.pytest-tmp-<用户名>/`，并禁用非必要的 pytest 缓存插件。这可避免不同账户共用系统临时目录、转换目录或旧缓存目录时因 ACL 权限导致 `WinError 5`。

## 批量评测

分层合成评测集包含中文普通论文、英文普通论文、图表密集论文、公式密集论文、参考文献复杂论文和异常排版论文六类，每类 5 篇。重新生成 30 篇 Word、golden 和 manifest：

```bash
cd backend
python scripts/generate_evaluation_corpus.py
```

Golden 同时保存解析目标和 `corrected_article`。后者用于模拟人工补充 ISSN、ORCID 等真实出版元数据，并统计人工校正后正式 JATS Schema 通过率。

```bash
cd backend
python evaluate.py
```

脚本会运行 `DocxParser`、Schema 自动修复与正式 DTD 校验，计算解析准确率、XML 合法率、原始/人工校正后 Schema 通过率、自动修复错误降幅与平均处理时间，并写入三份 Markdown 报告。评测不启动 Web 服务，也不调用外部 API。

## 校验规则

阻断性错误包括：标题、摘要、关键词或章节为空，XML 无法解析，以及缺少 JATS `journal-meta`、`article-meta`、`title-group`、`contrib-group`、`body` 或 `back` 节点。

非阻断性警告包括：作者、单位或参考文献为空，图片缺少图题，表格缺少表题或数据行，公式内容为空或 OMML 无法转换为 MathML，作者缺少 ORCID，章节没有正文段落，关键词少于 3 个，以及正文交叉引用 `rid` 指向不存在的 XML `id`。警告不会令 `passed` 变为 `false`，但建议在正式出版前人工复核。

## 决赛展示流程

1. 使用 `/api/demo-document` 获取仓库内置演示稿并调用批量转换。
2. 展示 `article/xml/validation/quality_report` 四类交付数据。
3. 人工修改 Article JSON 后调用 `/api/generate-xml`，展示质量分和 Schema 错误变化。
4. 调用 `/api/export-package` 下载包含 XML、JSON、验证报告、质量报告和媒体资源的 ZIP。
5. 运行 `python evaluate.py` 生成评测、消融实验和错误案例分析报告。

## 当前真实限制

- 标题、作者和单位使用启发式评分/关键词识别，复杂稿件可能需要更精细的样式映射。
- 暂不支持矩阵、多行公式、复杂重音符号等全部 OMML 结构；图片公式尚无 OCR，当前版本不调用商业 API。
- 复杂或非标准参考文献的细粒度字段准确率仍需人工复核。
- 缺少 ISSN、完整贡献者信息或特定期刊必填元数据时，正式 DTD 校验仍会失败。
- 复杂合并单元格、跨页表格、嵌套列表和期刊专属必填字段仍需增强。
- 当前批量转换为请求内顺序处理；生产环境可扩展任务队列、并发限制、进度查询、鉴权和临时结果定期清理。
- 当前质量评分为确定性的业务启发式评分，仍需结合出版社规则和人工终审。
