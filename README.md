# Word2JATS

## 企业出版增强

- 上传时可选择 `default`、中文期刊、英文期刊或 IMR 期刊 Profile；Profile 会影响摘要/关键词/图表题识别，并补齐期刊元数据。
- 参考文献会保留 `raw` 与 `mixed_citation`，并尝试解析作者、题名、来源、年份、卷期页码、DOI、出版类型和置信度；有结构化字段时输出 JATS `element-citation`。
- 校验结果分为 XML 合法性、正式 JATS Schema、业务规则和引用完整性。正式 Schema 未配置时明确返回 `jats_schema_valid: null`。
- 正式 Schema 失败后执行最多两轮白名单自动修复，自动处理图片 `xlink:href`、已知节点顺序和重复 ID 等确定性问题。
- 仓库已内置官方 JATS Publishing 1.4 MathML3 DTD 完整发行包，系统会从 `backend/schemas/` 自动发现主 DTD；也可通过 `JATS_SCHEMA_PATH` 指定其他本地 RNG/XSD/DTD 主文件。

Word2JATS 是一个面向学术出版的智能结构化转换原型。用户上传 `.docx` 学术论文后，系统使用可解释的规则算法提取文章结构，生成中间 JSON、JATS 风格 XML，并执行基础完整性校验。

## 技术栈

- 后端：Python、FastAPI、python-docx、lxml
- 前端：Vue 3、Vite、Element Plus、axios
- 测试：pytest、FastAPI TestClient

## 快速启动

Docker 一键启动：

```bash
docker compose up --build
```

请先启动 Docker Desktop（Linux containers）。启动后访问 `http://localhost:8080`，前端容器通过 Nginx 将 `/api` 请求转发到后端。

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`。可以选择一个或多个 `.docx` 文件并点击“开始批量转换”，随后查看每篇稿件的状态、结构化 JSON、JATS XML 和校验结果。

转换完成后，可以进入“人工校正”标签页修改标题、摘要、关键词、作者、单位、章节、图题、表格和参考文献。点击“重新生成 XML”后，系统会基于校正后的文章数据更新 XML 与校验结果。

项目已附带测试稿件：

```text
sample_documents/word2jats_demo.docx
sample_documents/word2jats_feature_acceptance.docx
sample_documents/word2jats_image_edge_cases.docx
sample_documents/word2jats_omml_formulas.docx
```

- `word2jats_feature_acceptance.docx`：覆盖当前主要功能，包含图片、图题、公式、参考文献，以及中英文表题和 Word 表格。
- `word2jats_image_edge_cases.docx`：包含 3 张图片和 2 个图题，用于测试多余图片 caption 为空。
- `word2jats_omml_formulas.docx`：包含 Word 原生 OMML 分数、上标、根号和求和结构，用于测试 MathML 转换。

也可以重新生成测试稿件：

```bash
cd backend
python scripts/generate_sample_docx.py
```

## 本地评测

项目在 `backend/evaluation/goldens` 保存与测试 Word 同名的人工标注 JSON。运行以下命令可批量解析样本、计算准确率和耗时，并更新 `docs/评测报告.md`、`docs/消融实验报告.md` 与 `docs/错误案例分析.md`：

```bash
cd backend
python evaluate.py
```

评测指标覆盖元数据、章节、图表绑定、公式、参考文献、交叉引用、XML 合法率、JATS Schema 合规率和平均处理耗时。整个评测流程仅使用本地文件，不依赖外部 API。

## 当前支持

- 规则识别标题、作者、单位、摘要、关键词和多级章节
- 直接解析 DOCX `word/document.xml`，按真实文档顺序生成段落、图片、表格和公式节点流
- 从 DOCX `word/media` 提取内嵌图片，并识别中英文图题、显式列表、简单公式和参考文献
- 基于段落长度、数学符号/关键词及 Equation/公式样式识别基础数学公式，并生成带 CDATA 的 JATS `disp-formula`
- 提取 Word 原生 OMML，并将常见结构转换为 Presentation MathML 与基础 LaTeX，输出 JATS `alternatives`
- 识别“参考文献”或 `References` 部分，拆分常见编号并生成带 label 的 JATS `ref-list`
- 解析 Word 表格，按顺序绑定 `表1`、`表 1`、`Table 1` 等表题，并生成 JATS `table-wrap/table/thead/tbody`
- 识别正文中的图、表、公式和参考文献引用，并生成 JATS `xref` 混合内容节点
- 生成更接近 JATS Publishing 1.4 的 `journal-meta/article-meta/body/back` 结构，支持 DOI、语言、文章类型、期刊、出版者、学科、出版日期及作者-单位关联
- 生成格式化 JATS 风格 XML，正确转义 XML 特殊字符
- 校验标题、摘要、关键词、章节、XML 合法性，以及 JATS `journal-meta`、`article-meta`、`title-group`、`contrib-group`、`body` 和 `back` 节点
- 提示作者、单位、参考文献、图题、表题、空表格、公式内容、ORCID、空章节、关键词数量和无效交叉引用等出版质量问题
- 提供 XML 复制与下载
- 支持多文件批量转换，逐篇展示成功、失败、警告数和错误数
- 支持下载单篇 XML，以及包含 XML、JSON、校验报告、媒体文件和 manifest 的 ZIP 结果包
- 支持人工校正结构化数据并重新生成 XML
- 基于元数据、结构、Schema、图表、公式、参考文献和交叉引用生成 0-100 质量分、问题定位与修复建议
- 展示 Schema 自动修复前后错误数量、已应用修复和仍需人工处理的问题
- 提供内置演示稿一键加载、首页能力卡片、批量质量状态与可复现 Docker/CI 流程

## 项目结构

```text
backend/   FastAPI API、解析器、XML 生成器、校验器与测试
frontend/  Vue 3 单页转换工作台
```

## 决赛展示流程

1. 执行 `docker compose up --build`，访问 `http://localhost:8080`。
2. 点击“一键加载演示数据”，展示从 Word 文档流到结构化 JSON、JATS XML 的完整转换。
3. 在“质量报告”查看总分、七项分项得分、问题定位与修复建议。
4. 在“校验结果”分别展示 XML 合法性、正式 JATS Schema、业务规则与交叉引用检查。
5. 进入“人工校正”修改元数据或参考文献，点击“重新生成 XML”展示质量闭环。
6. 在批量列表展示质量分、错误、警告和导出状态，并下载 XML 或完整 ZIP 交付包。
7. 展示 `docs/评测报告.md`、`docs/消融实验报告.md` 与 `docs/错误案例分析.md`。

## 当前真实限制

- 当前使用启发式规则，复杂排版、多人多单位映射可能需要人工校正。
- 暂不支持矩阵、多行公式、复杂重音符号等全部 OMML 结构。
- 图片公式暂不支持 OCR；当前版本不调用商业 API。
- 参考文献会保留 `raw` 与 `mixed_citation`，并启发式拆分作者、题名、来源、年份、卷期页码、DOI 和出版类型；复杂或非标准引文仍可能需要人工校正。
- 系统已接入本地正式 JATS Publishing 1.4 DTD 校验，并与 XML 合法性、业务规则校验分开展示；当前生成结果仍可能因缺少 ISSN 等期刊级必填元数据而无法通过正式 DTD。
- 复杂合并单元格、跨页表格和嵌套列表仍可能需要人工校正。
- Profile 已支持规则与元数据默认值，但尚未覆盖所有期刊的专属必填字段和许可策略。
- 当前批量转换按上传顺序逐篇执行，适合比赛原型；大规模任务可进一步扩展异步队列、进度查询和结果过期清理。
- 当前质量分是可解释的规则评分，不等同于出版社最终验收结论。
- Schema 自动修复不会编造 ISSN、DOI、ORCID、作者或出版日期；这些真实出版信息缺失时仍需人工补充。

## ZIP 结果包

批量转换列表中的每篇成功稿件均可下载独立 ZIP 包，内容包括：

```text
article.xml
article.json
validation_report.md
quality_report.json
manifest.json
media/
```

提交 `quality_report` 时 ZIP 会包含 `quality_report.json`；ZIP 导出只允许读取后端转换临时目录中的媒体文件，不接受任意本地路径。

更详细的服务说明见 [backend/README.md](backend/README.md) 和 [frontend/README.md](frontend/README.md)。
