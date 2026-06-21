# Word2JATS Backend

FastAPI 后端负责上传、DOCX 文档流解析、Article JSON 构建、JATS XML 生成、正式 Schema 校验、质量评分、人工校正后重生成、媒体预览和 ZIP 导出。

## 当前支持

| 能力 | 状态 |
| --- | --- |
| DOCX 真实文档流解析与原文映射 | 已支持 |
| 图片、表格、列表、章节归属与可视化预览 | 已支持 |
| OMML 转 MathML/LaTeX 与稳定降级 | 已支持 |
| 图、表、公式、参考文献交叉引用恢复 | 已支持 |
| 参考文献细粒度解析与 `element-citation` | 已支持 |
| JATS Publishing 1.3 MathML3 DTD 校验 | 已支持 |
| 官方样例 XML 结构对比 | 已支持 |
| Schema 白名单自动修复与人工校正闭环 | 已支持 |
| 批量转换与 ZIP 结果包 | 已支持 |

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
- 兼容单篇演示稿下载：`GET /api/demo-document`
- 演示稿清单：`GET /api/demo-documents`
- 白名单演示稿下载：`GET /api/demo-documents/{filename}`
- 安全媒体预览：`GET /api/media/{conversion_id}/{filename}`
- ZIP 导出：`POST /api/export-package`

Docker 运行时前端 Nginx 已设置 `client_max_body_size 100m`，可通过 `/api/batch-convert` 一次性提交 5 篇官方样例。

## 处理流程

1. `DocumentFlowParser` 直接解析 `word/document.xml` 和关系文件，按真实顺序生成段落、图片、表格和公式节点。
2. `DocxParser` 识别元数据、章节、图表、列表、公式、参考文献并绑定章节。
3. `OmmlConverter` 输出 MathML、LaTeX、转换状态、支持特性和复核问题。
4. `XrefResolver` 恢复图、表、公式和参考文献正文引用。
5. `JatsGenerator` 生成接近 JATS Publishing 1.3 的 XML，并输出官方 MathML3 DTD `DOCTYPE`、`dtd-version="1.3"` 和 `xlink` 命名空间。
6. `JatsSchemaValidator` 与 `JatsAutoFixer` 执行本地正式 Schema 校验和最多两轮确定性修复。
7. `ArticleValidator`、`QualityScorer` 汇总业务规则、引用完整性、质量分和修复建议。
8. `FlowViewBuilder`、`VisualPreviewBuilder` 为前端生成文档流映射和图表预览数据。

## 官方样例演示与对比

```text
样例-最新版/样例1/第一组/初始word.docx      -> 最终上线.xml
样例-最新版/样例2/第一组/初始文件.docx      -> 最终上线.xml
样例-最新版/样例3/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例4/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例5/第一组/初始文件.docx      -> 最终文件.xml
```

`/api/demo-documents` 默认返回上述 5 篇官方样例，并为重复的 `初始文件.docx` 生成唯一展示名。`/api/convert` 和 `/api/batch-convert` 对这些展示名会自动匹配同目录官方 XML，返回 `official_comparison`。语义指标 V2 对元数据、章节、图表、公式、参考文献、交叉引用和 XML 合规性分别评分，不使用全局标签计数替代转换质量。

当前五篇官方样例自动转换结果为：平均相似度 **91.4%**、最低单篇 **88%**、JATS 1.3 DTD 通过率 **100%**。运行以下命令可重新评测：

```bash
python evaluate_official_samples.py
```

报告输出到 `docs/官方样例对比报告.md`，并将源文档可恢复问题与 DOI、期刊 ID 等出版方补录字段分开列示。

`sample_documents/` 目录仅用于自动化回归测试和本地开发验证，不再作为前端默认一键演示数据。

全流程验收稿可重新生成：

```bash
python scripts/generate_sample_docx.py
```

后端集成测试会验证回归文档的结构数量、MathML 状态、JATS 标签、文档流映射、图表预览，以及人工补齐出版元数据后的正式 Schema 通过状态。

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

仓库内置官方 JATS Publishing 1.3 MathML3 DTD，并保留 JATS Publishing 1.4 MathML3 DTD 作为兼容资源。系统也支持通过 `JATS_SCHEMA_PATH` 指向本地 RNG、XSD 或 DTD；未配置环境变量时，校验器会根据 XML 的 `dtd-version` 自动选择匹配的本地 Schema。校验结果区分：

- `xml_well_formed`
- `jats_schema_valid`
- `business_rules`
- `xref_checks`
- `schema_errors`
- `auto_fix`

自动修复仅处理 `graphic/@xlink:href`、已知节点顺序、重复 ID 和无效 `xref/@rid` 等确定性问题；移除无效引用目标时会保留正文文字，不会编造 ISSN、DOI、ORCID。

## 测试与评测

```bash
python -m pytest -q
python evaluate.py
python evaluate_official_samples.py
```

`evaluate.py` 在系统临时目录按需生成 30 篇分层合成 Word，评测完成后自动删除。仓库保留 Golden JSON、manifest、评测报告、官方样例映射说明和本地回归文档，不长期保存 30 篇评测 DOCX。

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

- 启发式规则面对复杂排版、多作者多单位映射时仍可能需要人工校正。
- 不保证覆盖全部 Office Math；复杂嵌套矩阵、复杂分段、多重重音和未知 OMML 子结构会标记 `partial/failed`。
- 图片公式暂不支持 OCR，系统不调用商业 API。
- 复杂合并单元格、跨页表格、嵌套列表和非标准参考文献仍需人工复核。
- 正式 DTD 校验不会自动编造 ISSN、DOI、ORCID 等真实出版元数据。
- 当前批量转换为请求内顺序处理，生产环境仍可扩展任务队列、鉴权和结果过期清理。
- 质量分是可解释的规则评分，不等同于出版社最终验收结论。
