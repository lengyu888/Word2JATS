# Word2JATS Frontend

Vue 3 前端提供 DOCX 上传、批量转换、结构化审阅、人工校正、质量报告、原文映射、图表预览和结果导出。

## 技术栈

Vue 3、Vite、Element Plus、axios。

## 安装与启动

先启动后端 `http://127.0.0.1:8000`：

```bash
npm install
npm run dev
```

访问 `http://localhost:5173`。生产构建：

```bash
npm run build
```

也可在项目根目录执行 `docker compose up --build`，访问 `http://localhost:8080`。

## 页面能力

- Profile 选择、单篇或多篇 DOCX 上传
- 一键加载唯一完整验收稿
- 批量状态、质量分、错误数、警告数和导出状态
- 结构化 JSON 与 JATS XML 预览
- XML 复制、单篇下载和完整 ZIP 下载
- 人工校正标题、摘要、关键词、作者、单位、章节、图表、公式和参考文献
- XML 合法性、正式 JATS Schema、业务规则和交叉引用分区展示
- 质量总分、七项分项得分、错误定位和修复建议
- OMML `success/partial/failed`、支持特性、问题、MathML 和 LaTeX 展示
- 文档流节点到 JATS 标签、路径、章节和目标 ID 的对照
- 图片缩略图、大图、表格前 10 行、题注、引用次数和 JATS 片段预览

## 唯一演示数据

“一键加载演示数据”通过 `/api/demo-document` 获取：

```text
sample_documents/word2jats_final_acceptance.docx
```

它覆盖系统主要成功路径，并包含一个可控的复杂公式 `partial` 状态，方便现场展示质量报告和人工复核机制。

## 使用流程

1. 选择 Profile 并上传 DOCX，或一键加载演示数据。
2. 从批量列表选择文章，查看 JSON、XML、校验和质量报告。
3. 使用“文档流对照”解释 DOCX 到 JATS 的映射。
4. 使用“图表预览”核对媒体、表格、题注、引用和 XML 片段。
5. 在“人工校正”补充或修正结构化字段，点击“重新生成 XML”。
6. 查看重新执行后的正式 Schema、业务规则、交叉引用和质量分。
7. 下载 XML 或 ZIP 交付包。

## 决赛展示流程

1. 一键加载唯一验收稿。
2. 展示能力卡片与批量转换状态。
3. 展示文档流、图表、OMML、xref 和质量报告。
4. 人工补充出版元数据并重新生成。
5. 展示 Schema 状态变化和 ZIP 交付。

## 当前真实限制

- 复杂嵌套字段仍主要通过 JSON textarea 编辑，尚未全部表单化。
- 暂未提供转换历史、异步任务进度和用户权限。
- 尚未完成完整国际化与可访问性审计。
