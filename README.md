# Word2JATS

Word2JATS 是面向学术出版的 Word 智能结构化转换原型。系统直接解析 DOCX 真实文档流，将标题、作者、摘要、章节、图表、公式、参考文献和正文交叉引用转换为结构化 JSON 与接近 JATS Publishing 1.3 的 XML，并提供正式 DTD 校验、质量评分、人工校正和 ZIP 交付。

## 核心能力

| 能力 | 状态 |
| --- | --- |
| DOCX 真实文档流解析与原文映射 | 已支持 |
| 图片、表格、列表、章节归属与可视化预览 | 已支持 |
| TIFF 原件保留与浏览器 PNG 预览副本 | 已支持 |
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

## 官方基线与 JATS 1.3 对齐

竞赛官方 baseline 提供了 Word 内容抽取、JATS XML 模板生成和 JATS 到 PDF 的参考实现。本项目保留 Python + FastAPI + Vue 的既有架构，并将 XML 交付格式对齐到官方 JATS Publishing 1.3：输出包含 MathML3 DTD 的 `DOCTYPE`、`dtd-version="1.3"`、`xmlns:xlink`、`graphic/@xlink:href`、`journal-meta`、`article-meta`、`body` 和 `back/ref-list` 等核心结构。仓库内置官方 JATS Publishing 1.3 MathML3 DTD，同时保留 1.4 DTD 作为兼容校验资源；校验器会根据 XML 的 `dtd-version` 自动选择匹配的本地 DTD。

## 演示与测试文档

前端一键演示默认使用竞赛官方样例目录中的 5 篇第一组 Word 主稿，并将系统生成 XML 与同目录官方 XML 结果进行结构对比：

```text
样例-最新版/样例1/第一组/初始word.docx      -> 最终上线.xml
样例-最新版/样例2/第一组/初始文件.docx      -> 最终上线.xml
样例-最新版/样例3/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例4/第一组/初始文件.docx      -> 最终文件.xml
样例-最新版/样例5/第一组/初始文件.docx      -> 最终文件.xml
```

前端点击“一键加载官方样例”后，会通过 `/api/demo-documents` 获取官方样例清单，下载唯一展示名的 DOCX，并调用现有批量转换流程。每个转换结果会返回 `official_comparison`。语义指标 V2 分别评价元数据、章节结构、图表、公式、参考文献、交叉引用和 XML 合规性，并区分“源文档可恢复差异”与 DOI、期刊 ID 等“出版方补录差异”。旧接口 `/api/demo-document` 继续保留，用于兼容单篇演示稿调用方。

当前五篇官方样例自动转换结果：平均语义相似度 **96.6%**，最低单篇 **95%**，JATS Publishing 1.3 MathML3 DTD 通过率 **100%**。最新优化包含图表题注续行合并、图后风险人数小表识别、表注 `table-wrap-foot` 输出、caption 内交叉引用恢复、单位 `<aff><label>`、未编号一级章节 `<label>` 与编号章节 label/title 拆分输出、紧凑英文期刊参考文献尾部与 DOI URL 解析、逗号分隔英文期刊参考文献解析、结构化参考文献原始 `mixed-citation` 保真输出，以及 `fig1/tab9` 与 `fig001/tab009` 这类等价目标 ID 的语义归一。评测同时细分图表数量、题注、章节归属，以及公式数量、内容和章节归属；默认验收门槛为平均不低于 94%、单篇不低于 90%、DTD 通过率 100%。可通过以下命令复现并更新 `docs/官方样例对比报告.md`：

解析器还会区分 `Original Research` 等文章类型标签与真实标题，避免把 `Fig. 1 shows ...`、`Table 2 presents ...` 一类正文叙述误判为题注；作者识别支持普通数字/上标单位标记、学位后缀和 `Author information` 标签，单位识别同时利用文本与 Word `Affiliation` 样式。关键词后、首个正文标题前的图片按 `auxiliary_media` 保留并进入 ZIP，不再误生成正文 `<fig>`；长数字开头正文不会误判为章节，`Main Findings` 等常见讨论子标题按层级恢复。参考文献边界支持 `References and Notes`，作者年份制引文支持全名、`et al.`、叙述式引用及括号内分号分隔的多篇引用。所有作者年份引用都必须同时匹配参考文献中的第一作者与年份才会生成 `<xref>`，无法可靠匹配时保留原文。

```bash
cd backend
python evaluate_official_samples.py
```

图表与公式对象会返回 `confidence`、`status`、`evidence` 和 `issues`。图表匹配综合章节、文档流距离、编号与对象类型，支持保守识别图片化表格；歧义对象标记为 `need_review`。正文和原生表格单元格中的引用只有在目标 ID 真实存在时才生成 `<xref>`，缺失目标保留原文并进入校验与质量报告。

## 一键启动

先启动 Docker Desktop，然后在项目根目录执行：

```bash
docker compose up --build
```

Docker 前端 Nginx 已设置 `client_max_body_size 100m`，可支持 5 篇官方样例一次性批量上传。

访问：

- 前端：`http://localhost:8080`
- 后端健康检查：`http://localhost:8000/api/health`
- Swagger：`http://localhost:8000/docs`

本地开发：

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## 全流程测试

```bash
cd backend
python -m pytest -q
python evaluate_official_samples.py
```

发布前可执行无依赖的仓库自检，检查官方样例、JATS 1.3 DTD、Docker/前端入口和 README 一致性：

```bash
cd backend
python scripts/release_check.py
```

```bash
cd frontend
npm run build
```

`evaluate_official_samples.py` 使用 `样例-最新版` 中的竞赛官方 Word/XML 样例进行评测，输出系统生成 XML 与官方 XML 的语义相似度、分项质量和 JATS 1.3 DTD 通过率。报告输出到：

- `docs/官方样例对比报告.md`

## 使用流程

1. 选择期刊 Profile，上传 DOCX 或一键加载官方样例。
2. 查看结构化 JSON、JATS XML、校验结果和质量报告。
3. 在“文档流对照”查看原文节点到 JATS 标签的映射。
4. 在“图表预览”核对图片、表格、题注、引用和 JATS 片段。
5. 在“人工校正”补充 ORCID、ISSN、DOI 等真实出版元数据并重新生成 XML。
6. 再次执行业务规则、交叉引用和正式 JATS Schema 校验。
7. 下载单篇 XML 或包含 JSON、XML、报告和媒体文件的 ZIP 交付包。

每次转换响应还会返回 `processing_stats`，包含耗时、源文档流节点数、图表/公式/参考文献数量、校验错误数和 Schema 自动修复轮次，便于答辩展示和回归比较。

## 决赛展示流程

1. 执行 `docker compose up --build` 并访问 `http://localhost:8080`。
2. 点击“一键加载官方样例”，批量转换 5 篇官方 Word 主稿，在“官方对比”Tab 展示总分、七个分项、可恢复差异和出版方补录差异。
3. 展示文档流对照、图表预览、OMML 转换和正文交叉引用恢复。
4. 展示质量总分、分项得分、问题定位和修复建议。
5. 在人工校正页补充出版元数据，重新生成 XML 并展示 Schema 状态变化。
6. 下载 ZIP 交付包，最后展示官方样例对比报告。

发布前再执行 `python -m pytest -q`、`python evaluate_official_samples.py`、`python scripts/release_check.py` 和前端 `npm run build`，形成可复现的交付门禁。

## API

- `GET /api/health`
- `GET /api/profiles`
- `GET /api/demo-document`
- `GET /api/demo-documents`
- `GET /api/demo-documents/{filename}`
- `GET /api/media/{conversion_id}/{filename}`
- `POST /api/convert`
- `POST /api/batch-convert`
- `POST /api/generate-xml`
- `POST /api/export-package`

媒体接口仅允许读取对应转换任务的受控临时目录，并校验转换 ID、文件名、扩展名和解析后的真实路径。
对于 Word 内嵌 `.tif/.tiff`，系统保留原始 TIFF 作为 JATS/ZIP 交付媒体，并生成受尺寸限制的 PNG `preview_url` 供浏览器预览；不以预览副本替换正式原件。

## 当前真实限制

- 启发式规则面对复杂排版、多作者多单位映射时仍可能需要人工校正。
- 作者年份制引用在同作者同年歧义、缺失年份或非标准姓名顺序下可能保留原文并提示复核。
- 不保证覆盖全部 Office Math；复杂嵌套矩阵、复杂分段、多重重音和未知 OMML 子结构会标记 `partial/failed`。
- 图片公式暂不支持 OCR，系统不调用商业 API。
- 复杂合并单元格、跨页表格、嵌套列表和非标准参考文献仍需人工复核。
- `auxiliary_media` 保留正文前图片但不猜测其出版语义；图形摘要、作者照片等最终位置仍需按期刊要求确认。
- 正式 DTD 校验不会自动编造 ISSN、DOI、ORCID 等真实出版元数据。
- 当前批量转换为请求内顺序处理，生产环境仍可扩展任务队列、鉴权和结果过期清理。
- 质量分是可解释的规则评分，不等同于出版社最终验收结论。
- `processing_stats` 是本次请求的运行审计摘要，不代表生产环境的长期性能基准。

更多说明见 [backend/README.md](backend/README.md) 和 [frontend/README.md](frontend/README.md)。
