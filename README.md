# Word2JATS

Word2JATS 是面向学术出版的 Word 智能结构化转换原型。系统直接解析 DOCX 真实文档流，将标题、作者、摘要、章节、图表、公式、参考文献和正文交叉引用转换为结构化 JSON 与接近 JATS Publishing 1.4 的 XML，并提供正式 DTD 校验、质量评分、人工校正和 ZIP 交付。

## 核心能力

| 能力 | 状态 |
| --- | --- |
| DOCX 真实文档流解析与原文映射 | 已支持 |
| 图片、表格、列表、章节归属与可视化预览 | 已支持 |
| OMML 转 MathML/LaTeX 与稳定降级 | 已支持 |
| 图、表、公式、参考文献交叉引用恢复 | 已支持 |
| 参考文献细粒度解析与 `element-citation` | 已支持 |
| JATS Publishing 1.4 MathML3 DTD 校验 | 已支持 |
| Schema 白名单自动修复与人工校正闭环 | 已支持 |
| 批量转换与 ZIP 结果包 | 已支持 |

## 演示与测试文档

仓库提供两篇前端演示文档：

```text
sample_documents/word2jats_final_acceptance.docx
sample_documents/真实参考论文.docx
```

`word2jats_final_acceptance.docx` 是系统全流程验收稿，覆盖元数据、多级章节、列表、中英文图题和表题、图片、Word 表格、正文交叉引用、普通与扩展 OMML、可控 `partial` 降级、参考文献和人工校正场景。`真实参考论文.docx` 用于观察真实论文排版下的规则识别效果。

前端点击“一键加载两篇演示数据”后，会通过 `/api/demo-documents` 获取两篇文档，并调用现有批量转换流程。旧接口 `/api/demo-document` 继续保留，用于兼容仅加载全流程验收稿的调用方。

重新生成：

```bash
cd backend
python scripts/generate_sample_docx.py
```

## 一键启动

先启动 Docker Desktop，然后在项目根目录执行：

```bash
docker compose up --build
```

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
python evaluate.py
```

```bash
cd frontend
npm run build
```

`evaluate.py` 会在系统临时目录生成六类、共 30 篇分层合成评测语料，完成评测后自动清理，不会在 `sample_documents` 中堆积 DOCX。Golden JSON 与评测清单位于 `backend/evaluation/`，报告输出到：

- `docs/评测报告.md`
- `docs/消融实验报告.md`
- `docs/错误案例分析.md`

## 使用流程

1. 选择期刊 Profile，上传 DOCX 或一键加载两篇演示文档。
2. 查看结构化 JSON、JATS XML、校验结果和质量报告。
3. 在“文档流对照”查看原文节点到 JATS 标签的映射。
4. 在“图表预览”核对图片、表格、题注、引用和 JATS 片段。
5. 在“人工校正”补充 ORCID、ISSN、DOI 等真实出版元数据并重新生成 XML。
6. 再次执行业务规则、交叉引用和正式 JATS Schema 校验。
7. 下载单篇 XML 或包含 JSON、XML、报告和媒体文件的 ZIP 交付包。

## 决赛展示流程

1. 执行 `docker compose up --build` 并访问 `http://localhost:8080`。
2. 点击“一键加载两篇演示数据”，对比全流程验收稿与真实参考论文的转换结果。
3. 展示文档流对照、图表预览、OMML 转换和正文交叉引用恢复。
4. 展示质量总分、分项得分、问题定位和修复建议。
5. 在人工校正页补充出版元数据，重新生成 XML 并展示 Schema 状态变化。
6. 下载 ZIP 交付包，最后展示自动生成的 30 篇评测与消融实验报告。

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

## 当前真实限制

- 启发式规则面对复杂排版、多作者多单位映射时仍可能需要人工校正。
- 不保证覆盖全部 Office Math；复杂嵌套矩阵、复杂分段、多重重音和未知 OMML 子结构会标记 `partial/failed`。
- 图片公式暂不支持 OCR，系统不调用商业 API。
- 复杂合并单元格、跨页表格、嵌套列表和非标准参考文献仍需人工复核。
- 正式 DTD 校验不会自动编造 ISSN、DOI、ORCID 等真实出版元数据。
- 当前批量转换为请求内顺序处理，生产环境仍可扩展任务队列、鉴权和结果过期清理。
- 质量分是可解释的规则评分，不等同于出版社最终验收结论。

更多说明见 [backend/README.md](backend/README.md) 和 [frontend/README.md](frontend/README.md)。
