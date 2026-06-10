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
- 人工校正后生成 XML：`POST http://127.0.0.1:8000/api/generate-xml`

转换接口使用 `multipart/form-data`，字段名为 `file`，仅接受 `.docx`。

```bash
curl -F "file=@paper.docx" http://127.0.0.1:8000/api/convert
```

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

## 处理流程

1. 将上传文件保存到请求级临时目录。
2. `DocxParser` 按段落顺序提取标题、前置信息、正文结构及文后参考文献，并从 DOCX ZIP 的 `word/media` 提取图片。
3. `JatsGenerator` 使用 lxml 构建并格式化 XML。
4. `ArticleValidator` 执行基础 JATS 结构与出版质量校验。
5. 请求结束后清理临时文件。

## 测试

```bash
python -m pytest -q
```

测试覆盖核心解析规则、XML 生成、校验器、健康检查、转换接口、人工校正生成接口和错误文件类型。

## 校验规则

阻断性错误包括：标题、摘要、关键词或章节为空，XML 无法解析，以及缺少 JATS `article-meta` 或 `body` 节点。

非阻断性警告包括：作者、单位或参考文献为空，图片缺少图题，公式内容为空，作者缺少 ORCID，章节没有正文段落，以及关键词少于 3 个。警告不会令 `passed` 变为 `false`，但建议在正式出版前人工复核。

## 当前限制与扩展方向

- 标题、作者和单位使用启发式评分/关键词识别，复杂稿件可能需要更精细的样式映射。
- 图片保存到 `backend/temp/<转换ID>/media`，JSON 和 XML 使用相对路径。
- 图题支持 `图1`、`图 1`、`图1-1`、`Fig. 1` 和 `Figure 1` 等形式，并按出现顺序与图片绑定。
- 图片和图题数量不一致时不会报错：多余图片 caption 为空，多余图题生成为无 graphic 的 caption-only figure。
- 基础公式识别使用短段落、数学符号/关键词及 Equation/公式样式规则，输出 `id/content/type/section_index` 结构，并生成带 CDATA 的 JATS `disp-formula/tex-math`。
- 参考文献识别支持“参考文献”与 `References` 标题，以及 `[1]`、`1.`、`（1）` 编号；编号拆入 `label`，清理后的引文保存在 `raw`，XML 输出 `ref-list/ref/label/mixed-citation`。
- 后续可扩展 Word OMML 转 MathML、LaTeX-OCR 和 Mathpix；当前版本不调用商业公式识别 API。
- 参考文献尚未拆分为作者、文章题名、期刊名、年份等细粒度 JATS 元素。
- 当前是 JATS 思路的 XML，不包含正式 DTD/XSD 校验。
- 可扩展图片静态资源接口、转换结果 ZIP、标准 JATS 校验、表格解析和异步任务队列。
