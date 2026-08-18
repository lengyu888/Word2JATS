# Word2JATS Backend

FastAPI 后端负责 `.doc`/`.docx` 上传、旧版 Word 安全预转换、DOCX 文档流解析、Article JSON 构建、JATS XML 生成、正式 Schema 校验、质量评分、人工校正后重生成、媒体预览和 ZIP 导出。

## 当前支持

| 能力 | 状态 |
| --- | --- |
| LibreOffice Headless `.doc` → `.docx` 预转换 | 已支持 |
| DOCX 真实文档流解析与原文映射 | 已支持 |
| 图片、表格、列表、章节归属与可视化预览 | 已支持 |
| TIFF 原件保留与 PNG 预览副本 | 已支持 |
| 正文前辅助媒体保留与正文 `fig` 隔离 | 已支持 |
| OMML 转 MathML/LaTeX 与稳定降级 | 已支持 |
| 图、表、公式、数字制及作者年份制参考文献交叉引用恢复 | 已支持 |
| 参考文献细粒度解析与 `element-citation` | 已支持 |
| JATS Publishing 1.3 MathML3 DTD 校验 | 已支持 |
| 官方样例 XML 结构对比 | 已支持 |
| 图表/公式结构证据、置信度与保守复核状态 | 已支持 |
| xref 目标存在性过滤与缺失目标定位 | 已支持 |
| Schema 白名单自动修复与人工校正闭环 | 已支持 |
| 批量转换与 ZIP 结果包 | 已支持 |
| 转换耗时、节点数量与校验轮次审计统计 | 已支持 |

## 技术栈

Python 3.10+、FastAPI、python-docx、lxml、Pydantic、PyYAML、pytest；旧版 `.doc` 转换依赖本地 LibreOffice Writer，Docker 镜像已内置。

## 安装与启动

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

本机直接处理 `.doc` 时，请安装 LibreOffice 并将 `soffice` 加入 PATH，或设置 `WORD2JATS_SOFFICE=C:\Program Files\LibreOffice\program\soffice.exe`。转换器使用独立用户配置目录、120 秒超时和 OOXML ZIP 完整性检查；未安装时 `.doc` 请求返回明确的 400，`.docx` 不受影响。

发布前自检（不依赖额外 Python 包）：

```bash
python scripts/release_check.py
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

1. `LegacyDocConverter` 对 `.doc` 调用本地 LibreOffice Headless，在任务独立目录中生成并验证临时 `.docx`；响应通过 `source_format`、`preprocessing.converted/converter/intermediate_format` 留下审计信息。
2. `DocumentFlowParser` 直接解析 `word/document.xml` 和关系文件，按真实顺序生成段落、图片、表格和公式节点。
3. `DocxParser` 识别元数据、章节、图表、列表、公式、参考文献并绑定章节；正文开始前的图片进入 `auxiliary_media`，继续参与 ZIP 交付但不误生成正文 `fig`。
4. `OmmlConverter` 输出 MathML、LaTeX、转换状态、支持特性和复核问题。
5. `StructureEvidence` 对图表绑定与独立公式分类给出置信度、证据和复核状态；`XrefResolver` 恢复数字制及作者年份制引用，并且仅对实际存在的图、表、公式和参考文献 ID 生成正文引用。
6. `JatsGenerator` 生成接近 JATS Publishing 1.3 的 XML，并输出官方 MathML3 DTD `DOCTYPE`、`dtd-version="1.3"` 和 `xlink` 命名空间。
7. `JatsSchemaValidator` 与 `JatsAutoFixer` 执行本地正式 Schema 校验和最多两轮确定性修复。
8. `ArticleValidator`、`QualityScorer` 汇总业务规则、引用完整性、质量分和修复建议。
9. `FlowViewBuilder`、`VisualPreviewBuilder` 为前端生成文档流映射和图表预览数据。
   TIFF 图片会在受控媒体目录中额外生成 PNG 预览副本；JATS 与 ZIP 保持指向原始 TIFF。
9. 路由层附加返回 `processing_stats`，记录耗时、源节点数、结构对象数、校验错误数和 Schema 自动修复轮次，便于回归审计。

## 官方样例演示与对比

```text
样例-最新版/样例1/第一组/初始word.docx      -> 最终上线.xml
样例-最新版/样例2/第一组/初始文件.docx      -> 最终上线.xml
样例-最新版/样例3/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例4/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例5/第一组/初始文件.docx      -> 最终文件.xml
```

`/api/demo-documents` 默认返回上述 5 篇官方样例，并为重复的 `初始文件.docx` 生成唯一展示名。`/api/convert` 和 `/api/batch-convert` 对这些展示名会自动匹配同目录官方 XML，返回 `official_comparison`。语义指标 V2 对元数据、章节、图表、公式、参考文献、交叉引用和 XML 合规性分别评分，不使用全局标签计数替代转换质量。

当前五篇官方样例自动转换结果为：平均相似度 **96.6%**、最低单篇 **95%**、JATS 1.3 DTD 通过率 **100%**。比较器额外输出图表数量、题注、章节归属和公式数量、内容、章节归属等细分指标；命令默认执行 94/90/100% 防回归门槛。最新优化包含图表题注续行合并、图后风险人数小表识别、表注 `table-wrap-foot` 输出、caption 内交叉引用恢复、单位 `<aff><label>`、未编号一级章节 `<label>` 与编号章节 label/title 拆分输出、紧凑英文期刊参考文献尾部与 DOI URL 解析、逗号分隔英文期刊参考文献解析、结构化参考文献原始 `mixed-citation` 保真输出，以及 `fig1/tab9` 与 `fig001/tab009` 这类等价目标 ID 的语义归一。旧版 Word 预转换后常见的命名标题样式可恢复章节层级；长正文中的多张内嵌公式图片不会被拆成多幅独立插图；带编号和公式上下文的图片可降级为 `image_formula`；紧邻图题的紧凑三列表图例不会混入正文表格。图表候选匹配器会综合章节、文档流距离、编号和对象类型识别图片化表格，JATS 生成器也会恢复 Word 原生表格单元格内的有效交叉引用。运行以下命令可重新评测：

通用规则增强了文章类型标签与真实标题的区分，并恢复旧版 Word 转换常见的多行标题、姓名首字母作者列表、整体偏移的数字标题样式和误继承标题样式的长正文。题注识别利用样式、编号分隔符和上下文，避免把 `Fig. 1 shows ...`、`Table 2 presents ...` 误分类为图表题；小型图例表会归入图片上下文，前置/后置表题按文档流方向绑定，Scheme 标签与图题正文分离。旧文档中以图片保存的公式作为 `image_formula` 保留，JATS 输出 `disp-formula/graphic`，原始媒体继续进入 ZIP，无法转录 MathML 时明确标记人工复核；单行 Word 表格使用合法 `tbody`，不会生成只有 `thead` 的无效 JATS 表。作者与单位恢复会综合普通数字/上标标记、学位后缀、`Author information` 标签、机构文本和 Word `Affiliation` 样式；参考文献边界支持 `References and Notes`。作者年份制引用可处理全名、`et al.`、叙述式引用及括号内分号分隔的多篇引用；只有第一作者和年份同时命中现有参考文献时才输出 JATS `xref`。

```bash
python evaluate_official_samples.py
```

报告输出到 `docs/官方样例对比报告.md`，并将源文档可恢复问题与 DOI、期刊 ID 等出版方补录字段分开列示。

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
python evaluate_official_samples.py
```

`evaluate_official_samples.py` 使用 `样例-最新版` 中的竞赛官方 Word/XML 样例，输出官方对比报告并执行 94/90/100% 防回归门槛。项目评测入口统一为官方样例评测，避免多套评测口径混用。

指标包括元数据、章节结构、图表、公式、参考文献、交叉引用、XML 合规性、JATS 1.3 DTD 通过率，以及源文档可恢复差异和出版方补录差异。

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
- `.doc` 支持依赖 LibreOffice 的导入过滤器；损坏 OLE 文档、旧 Equation Editor 对象、宏或嵌入对象可能降级，系统不会执行宏，也不会声称能无损恢复已丢失的公式语义。
- 作者年份制引用在同作者同年歧义、缺失年份或非标准姓名顺序下可能保留原文并提示复核。
- 不保证覆盖全部 Office Math；复杂嵌套矩阵、复杂分段、多重重音和未知 OMML 子结构会标记 `partial/failed`。
- 图片公式暂不支持 OCR，系统不调用商业 API。
- 复杂合并单元格、跨页表格、嵌套列表和非标准参考文献仍需人工复核。
- `auxiliary_media` 不自动判断图形摘要、作者照片等具体出版语义，最终放置方式仍需按期刊 Profile 或人工校正确认。
- 正式 DTD 校验不会自动编造 ISSN、DOI、ORCID 等真实出版元数据。
- 当前批量转换为请求内顺序处理，生产环境仍可扩展任务队列、鉴权和结果过期清理。
- 质量分是可解释的规则评分，不等同于出版社最终验收结论。
- 当前统计是单次请求级审计信息，尚未替代生产环境的集中式指标系统。
