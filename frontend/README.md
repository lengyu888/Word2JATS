# Word2JATS Frontend

## 功能状态

| 能力 | 当前状态 |
| --- | --- |
| Profile 选择与批量上传 | 已支持 |
| JSON/XML/校验/质量报告展示 | 已支持 |
| Schema 自动修复记录展示 | 已支持 |
| 人工校正后重新生成 XML | 已支持 |
| 完整嵌套字段表单、国际化与可访问性审计 | 尚未完成 |

## 企业出版增强界面

- 上传区可选择期刊 Profile，并将 Profile 随单篇或批量转换请求提交。
- 校验面板单独展示 JATS Schema 状态与 `schema_errors`。
- 校验面板展示 Schema 自动修复前后错误数量、已应用修复记录和仍需人工处理的问题。
- “质量报告”Tab 汇总 XML 合法性、JATS Schema、业务完整性和引用完整性。
- 人工校正页的 references JSON 支持编辑作者、题名、来源、年份、卷期页码、DOI、出版类型和解析置信度。

Vue 3 单页前端提供 `.docx` 上传、转换状态反馈、结构化 JSON/JATS XML 审阅、校验结果展示，以及 XML 复制与下载。

## 技术栈

Vue 3、Vite、Element Plus、axios。

## 安装与启动

项目根目录一键启动：

```bash
docker compose up --build
```

请先启动 Docker Desktop（Linux containers），再访问 `http://localhost:8080`。

先确保后端运行在 `http://127.0.0.1:8000`，再执行：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。Vite 会把 `/api` 请求代理到后端。

生产构建：

```bash
npm run build
```

## 使用流程

1. 拖入或选择一个或多个 `.docx` 学术稿件。
2. 点击“开始批量转换”并等待逐篇处理完成。
3. 在批量转换列表查看成功、失败、警告数和错误数，并选择稿件进入详情。
4. 在“人工校正”标签页修改标题、摘要、关键词及嵌套文章数据。
5. 点击“重新生成 XML”，更新 XML 预览和校验结果。
6. 使用 XML 标签页复制或下载 XML，或在批量列表下载单篇 XML 和完整 ZIP 结果包。

## 当前支持

- `.docx` 文件类型限制及单文件上传
- 多文件选择与批量转换状态列表
- 转换 loading 与错误提示
- 格式化 JSON/XML 预览
- XML 复制和浏览器下载
- 单篇 XML 下载和完整 ZIP 结果包下载
- 错误、警告和统计信息展示
- 校验面板展示通过项、错误项和警告项数量，并按绿色、红色、黄色区分状态
- 校验面板独立展示正文交叉引用检查结果，并将不存在的引用目标作为黄色警告展示
- 人工校正文章结构并重新生成 XML
- 结构化 JSON 展示提取后的 figures，人工校正页可编辑图片 caption 和相对路径
- 结构化 JSON 展示 tables，人工校正页可编辑表题、二维 rows 和 section_index，并重新生成 `table-wrap`
- 结构化 JSON 展示 formulas 的 `content/omml/mathml/latex/type`，人工校正页可编辑后重新生成 `disp-formula/alternatives`
- 结构化 JSON 展示 `id/label/raw` references，人工校正页可编辑后重新生成 `ref-list`
- 人工校正页支持 DOI、ISSN、文章类型、语言、期刊、出版者、学科和出版日期等 JATS Publishing 元数据
- 作者可在 authors JSON 中使用 `affiliation_ids` 编辑与 `aff1`、`aff2` 等单位的关联
- 首页展示五类核心能力卡片，并支持一键加载内置演示稿
- 质量报告展示总分、等级、七项分项得分、问题位置与修复建议
- 批量列表展示质量分、错误数、警告数和 ZIP 导出状态
- Schema 自动修复记录与剩余人工问题分区展示
- 响应式布局

## 决赛展示流程

1. 点击“一键加载演示数据”完成现场快速转换。
2. 使用首页能力卡片介绍文档流、Schema、OMML、xref 和批量交付能力。
3. 在质量报告展示总分、七项分项得分、错误定位和修复建议。
4. 在人工校正页修改结构化数据并重新生成 XML。
5. 在批量列表展示质量分、错误、警告和 ZIP 导出状态。

## 当前真实限制

- 暂未提供原文与结构化结果的逐段可视化对照。
- 暂未提供图片媒体预览、转换历史和异步任务进度。
- 复杂嵌套 JSON 仍通过 textarea 编辑，尚未全部表单化。
- 尚未完成完整国际化和可访问性审计。
