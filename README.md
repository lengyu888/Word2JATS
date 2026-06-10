# Word2JATS

Word2JATS 是一个面向学术出版的智能结构化转换原型。用户上传 `.docx` 学术论文后，系统使用可解释的规则算法提取文章结构，生成中间 JSON、JATS 风格 XML，并执行基础完整性校验。

## 技术栈

- 后端：Python、FastAPI、python-docx、lxml
- 前端：Vue 3、Vite、Element Plus、axios
- 测试：pytest、FastAPI TestClient

## 快速启动

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

浏览器访问 `http://localhost:5173`。选择 `.docx` 文件并点击“开始转换”，即可查看结构化 JSON、JATS XML 和校验结果，并下载 XML。

转换完成后，可以进入“人工校正”标签页修改标题、摘要、关键词、作者、单位、章节、图题、表格和参考文献。点击“重新生成 XML”后，系统会基于校正后的文章数据更新 XML 与校验结果。

项目已附带测试稿件：

```text
sample_documents/word2jats_demo.docx
sample_documents/word2jats_feature_acceptance.docx
sample_documents/word2jats_image_edge_cases.docx
```

- `word2jats_feature_acceptance.docx`：覆盖当前主要功能，包含图片、图题、公式、参考文献，以及中英文表题和 Word 表格。
- `word2jats_image_edge_cases.docx`：包含 3 张图片和 2 个图题，用于测试多余图片 caption 为空。

也可以重新生成测试稿件：

```bash
cd backend
python scripts/generate_sample_docx.py
```

## 本地评测

项目在 `backend/evaluation/goldens` 保存与测试 Word 同名的人工标注 JSON。运行以下命令可批量解析样本、计算准确率和耗时，并更新 `docs/评测报告.md`：

```bash
cd backend
python evaluate.py
```

评测指标包括标题、摘要、关键词 precision/recall、章节标题、图片/公式/参考文献数量准确率、XML 合法率和平均处理耗时。整个评测流程仅使用本地文件，不依赖外部 API。

## 当前支持

- 规则识别标题、作者、单位、摘要、关键词和多级章节
- 从 DOCX `word/media` 提取内嵌图片，并识别中英文图题、显式列表、简单公式和参考文献
- 基于段落长度、数学符号/关键词及 Equation/公式样式识别基础数学公式，并生成带 CDATA 的 JATS `disp-formula`
- 识别“参考文献”或 `References` 部分，拆分常见编号并生成带 label 的 JATS `ref-list`
- 解析 Word 表格，按顺序绑定 `表1`、`表 1`、`Table 1` 等表题，并生成 JATS `table-wrap/table/thead/tbody`
- 生成更接近 JATS Publishing 1.4 的 `journal-meta/article-meta/body/back` 结构，支持 DOI、语言、文章类型、期刊、出版者、学科、出版日期及作者-单位关联
- 生成格式化 JATS 风格 XML，正确转义 XML 特殊字符
- 校验标题、摘要、关键词、章节、XML 合法性，以及 JATS `journal-meta`、`article-meta`、`title-group`、`contrib-group`、`body` 和 `back` 节点
- 提示作者、单位、参考文献、图题、表题、空表格、公式内容、ORCID、空章节和关键词数量等出版质量问题
- 提供 XML 复制与下载
- 支持人工校正结构化数据并重新生成 XML

## 项目结构

```text
backend/   FastAPI API、解析器、XML 生成器、校验器与测试
frontend/  Vue 3 单页转换工作台
```

## MVP 限制与扩展方向

- 当前使用启发式规则，复杂排版、多人多单位映射可能需要人工校正。
- 图片会从 DOCX 压缩包的 `word/media` 提取到 `backend/temp`，并在 JSON/XML 中记录相对路径；MVP API 暂不单独提供图片下载接口。
- 图片和图题按出现顺序绑定。多余图片保留空 caption，多余图题保留为 caption-only figure。
- 表格与表题按各自在文档中的出现顺序绑定；多余表格保留空 caption，多余表题保留为空 rows 的表格对象。
- 当前公式识别是基础规则版本，支持常见运算符、希腊字母、`frac`、`sqrt`、`lim`、`log`、`sin`、`cos` 和 Equation/公式样式，并输出带 CDATA 的 `tex-math`。
- 后续可扩展 Word OMML 转 MathML、LaTeX-OCR，以及 Mathpix 等第三方公式识别方案；当前 MVP 不调用商业 API。
- 参考文献当前保留清理编号后的原始引文文本，尚未进一步拆分作者、题名、期刊、年份等字段。
- 当前输出更接近 JATS Publishing 结构，但校验仍为原型级结构检查，尚未接入正式 JATS DTD/XSD 校验。
- 列表优先识别 Word 编号属性及常见文本前缀，暂未保留嵌套层级。
- 后续可增加 JATS DTD/XSD 校验、DOCX/XML/图片打包下载、在线结构编辑、引用拆分与批量转换。

更详细的服务说明见 [backend/README.md](backend/README.md) 和 [frontend/README.md](frontend/README.md)。
