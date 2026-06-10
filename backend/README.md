# Word2JATS Backend

FastAPI 后端负责接收 Word 文档、执行规则解析、生成 JATS 风格 XML，并返回基础校验结果。服务无数据库、无商业 API 依赖，适合作为比赛原型和后续算法迭代基线。

## 技术栈

Python 3.10+、FastAPI、python-docx、lxml、Pydantic、pytest。

## 安装与启动

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
6. `ArticleValidator` 执行基础 JATS 结构、出版质量及交叉引用目标校验。
7. 请求结束后清理临时文件。

## 测试

```bash
python -m pytest -q
```

测试覆盖核心解析规则、XML 生成、校验器、健康检查、转换接口、人工校正生成接口和错误文件类型。

## 批量评测

`evaluation/goldens` 中的人工标注 JSON 与 `sample_documents` 下的 Word 文件按文件名对应。Golden 只需标注评测使用的 `title`、`abstract`、`keywords`、`sections`、`figures`、`formulas` 和 `references` 字段。

```bash
cd backend
python evaluate.py
```

脚本会运行 `DocxParser`、生成并解析 JATS XML，计算各项准确率与平均处理时间，并将 Markdown 报告写入 `docs/评测报告.md`。评测不启动 Web 服务，也不调用外部 API。

## 校验规则

阻断性错误包括：标题、摘要、关键词或章节为空，XML 无法解析，以及缺少 JATS `journal-meta`、`article-meta`、`title-group`、`contrib-group`、`body` 或 `back` 节点。

非阻断性警告包括：作者、单位或参考文献为空，图片缺少图题，表格缺少表题或数据行，公式内容为空或 OMML 无法转换为 MathML，作者缺少 ORCID，章节没有正文段落，关键词少于 3 个，以及正文交叉引用 `rid` 指向不存在的 XML `id`。警告不会令 `passed` 变为 `false`，但建议在正式出版前人工复核。

## 当前限制与扩展方向

- 标题、作者和单位使用启发式评分/关键词识别，复杂稿件可能需要更精细的样式映射。
- 图片保存到 `backend/temp/<转换ID>/media`，JSON 和 XML 使用相对路径。
- 文档流解析器识别普通段落、标题段落、章节、图题、表题、列表、含 `w:drawing` 的图片段落、含 `m:oMath/m:oMathPara` 的公式段落和 `w:tbl` 表格。
- 图片通过 `word/_rels/document.xml.rels` 的 `r:embed` 映射到 `word/media`，不再依赖 ZIP 媒体文件名排序推断位置。
- 图题支持 `图1`、`图 1`、`图1-1`、`Fig. 1` 和 `Figure 1` 等形式，并按出现顺序与图片绑定。
- 图片和图题数量不一致时不会报错：多余图片 caption 为空，多余图题生成为无 graphic 的 caption-only figure。
- Word 表格输出为 `tables` 数组，首行作为 JATS `thead`，其余行作为 `tbody`；支持 `表1`、`表 1`、`Table 1` 表题并按出现顺序绑定。
- 表格和表题数量不一致时不会报错：多余表格 caption 为空，多余表题生成为 rows 为空的 table 对象。
- 图片、表格和公式在节点出现时记录当前章节，题注只与同章节对象绑定，避免跨章节误关联。
- 正文交叉引用支持 `图1/图 1/Fig. 1/Figure 1`、`表1/表 1/Table 1`、`式（1）/公式（1）/Eq. (1)` 和 `[1]/[1,2]/[1-3]`。
- 一个段落可以生成多个 `xref`；参考文献组合与范围引用的 `rid` 使用空格分隔的 IDREFS，例如 `rid="ref1 ref2 ref3"`。
- Formula 输出 `id/content/omml/mathml/latex/type/section_index`；旧版 `plain_text` 与 `tex` 输入仍会被兼容归一化。
- OMML 基础转换支持分数、上下标、根号、求和、括号、普通变量和运算符，并生成 JATS `disp-formula/alternatives/mml:math/tex-math`。
- 基础规则公式继续使用短段落、数学符号/关键词及 Equation/公式样式识别，并作为 `tex-math` 回退输出。
- 参考文献识别支持“参考文献”与 `References` 标题，以及 `[1]`、`1.`、`（1）` 编号；编号拆入 `label`，清理后的引文保存在 `raw`，XML 输出 `ref-list/ref/label/mixed-citation`。
- 后续可扩展矩阵、多行公式、重音符号等 OMML 结构，以及 LaTeX-OCR 和 Mathpix；当前版本不调用商业公式识别 API。
- 参考文献尚未拆分为作者、文章题名、期刊名、年份等细粒度 JATS 元素。
- XML 根节点输出 JATS 1.4、语言与文章类型属性，front 包含 `journal-meta` 和 `article-meta`，并支持 DOI、出版日期、学科及作者-单位 xref。
- 当前输出更接近 JATS Publishing 结构，但校验仍为原型级节点检查，尚未使用正式 JATS Publishing DTD/XSD。
- 当前是 JATS 思路的 XML，不包含正式 DTD/XSD 校验。
- 可扩展图片静态资源接口、标准 JATS 校验、复杂合并单元格处理和异步任务队列。
- 当前批量转换为请求内顺序处理；生产环境可扩展任务队列、并发限制、进度查询、鉴权和临时结果定期清理。
