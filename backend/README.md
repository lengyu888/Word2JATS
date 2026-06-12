# Word2JATS Backend

FastAPI 后端负责上传、DOCX 文档流解析、Article JSON 构建、JATS XML 生成、正式 Schema 校验、质量评分、人工校正后重生成、媒体预览和 ZIP 导出。

## 技术栈

Python 3.10+、FastAPI、python-docx、lxml、Pydantic、PyYAML、pytest。

## 安装与启动

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

常用入口：

- 健康检查：`GET /api/health`
- Swagger：`http://127.0.0.1:8000/docs`
- 单篇转换：`POST /api/convert`
- 批量转换：`POST /api/batch-convert`
- 人工校正后生成：`POST /api/generate-xml`
- 演示稿下载：`GET /api/demo-document`
- 安全媒体预览：`GET /api/media/{conversion_id}/{filename}`
- ZIP 导出：`POST /api/export-package`

## 处理流程

1. `DocumentFlowParser` 直接解析 `word/document.xml` 和关系文件，按真实顺序生成段落、图片、表格和公式节点。
2. `DocxParser` 识别元数据、章节、图表、列表、公式、参考文献并绑定章节。
3. `OmmlConverter` 输出 MathML、LaTeX、转换状态、支持特性和复核问题。
4. `XrefResolver` 恢复图、表、公式和参考文献正文引用。
5. `JatsGenerator` 生成接近 JATS Publishing 1.4 的 XML。
6. `JatsSchemaValidator` 与 `JatsAutoFixer` 执行本地正式 Schema 校验和最多两轮确定性修复。
7. `ArticleValidator`、`QualityScorer` 汇总业务规则、引用完整性、质量分和修复建议。
8. `FlowViewBuilder`、`VisualPreviewBuilder` 为前端生成文档流映射和图表预览数据。

## 唯一验收文档

```text
sample_documents/word2jats_final_acceptance.docx
```

重新生成：

```bash
python scripts/generate_sample_docx.py
```

该文件覆盖完整成功路径和一个可控的复杂 OMML `partial` 路径。后端集成测试会验证其结构数量、MathML 状态、JATS 标签、文档流映射、图表预览，以及人工补齐出版元数据后的正式 Schema 通过状态。

## OMML 能力矩阵

| Office Math 结构 | MathML | LaTeX | 状态 |
| --- | --- | --- | --- |
| 分数、上下标、根号、括号 | `mfrac/msub/msup/msqrt/mfenced` | 基础命令 | success |
| 2D 矩阵 | `mtable/mtr/mtd` | `matrix` | success |
| Equation Array | 每行一个 `mtr` | `aligned` | success |
| 左大括号与多行分段 | `mfenced` + `mtable` | `cases` | success/partial |
| 求和、积分及上下限 | `munder/mover/munderover` | 带上下限命令 | success |
| hat、bar、dot、tilde | `mover accent=true` | 对应重音命令 | success |
| 未知或复杂嵌套结构 | 保留可识别内容 | 可读回退 | partial/failed |

## 正式 JATS Schema

仓库内置 JATS Publishing 1.4 MathML3 DTD，系统也支持通过 `JATS_SCHEMA_PATH` 指向本地 RNG、XSD 或 DTD。校验结果区分：

- `xml_well_formed`
- `jats_schema_valid`
- `business_rules`
- `xref_checks`
- `schema_errors`
- `auto_fix`

自动修复仅处理 `graphic/@xlink:href`、已知节点顺序和重复 ID 等确定性问题，不会编造 ISSN、DOI、ORCID。

## 测试与评测

```bash
python -m pytest -q
python evaluate.py
```

`evaluate.py` 在系统临时目录按需生成 30 篇分层合成 Word，评测完成后自动删除。仓库只提交 Golden JSON、manifest、评测报告和唯一验收 Word，不长期保存 30 篇评测 DOCX。

指标包括标题、摘要、关键词、章节、图表绑定、公式、参考文献、交叉引用、XML 合法率、原始 Schema 通过率、人工校正后 Schema 通过率和平均耗时。

## ZIP 结果包

```text
article.xml
article.json
validation_report.md
quality_report.json
manifest.json
media/
```

## 当前真实限制

- 复杂排版、多作者多单位映射仍可能需要人工校正。
- 复杂嵌套矩阵、复杂分段、多重重音、图片公式 OCR 尚未完整支持。
- 复杂合并单元格、跨页表格、嵌套列表和非标准参考文献仍需增强。
- 正式 Schema 通过依赖真实期刊级元数据。
- 大规模生产任务仍需异步队列、鉴权、并发限制和临时结果清理策略。
