# Word2JATS Frontend

Vue 3 单页前端提供 `.docx` 上传、转换状态反馈、结构化 JSON/JATS XML 审阅、校验结果展示，以及 XML 复制与下载。

## 技术栈

Vue 3、Vite、Element Plus、axios。

## 安装与启动

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

1. 拖入或选择一个 `.docx` 学术稿件。
2. 点击“开始转换”并等待处理完成。
3. 在“结构化 JSON”“JATS XML”“校验结果”标签页审阅输出。
4. 在“人工校正”标签页修改标题、摘要、关键词及嵌套文章数据。
5. 点击“重新生成 XML”，更新 XML 预览和校验结果。
6. 使用 XML 标签页中的按钮复制或下载 `article.xml`。

## 当前支持

- `.docx` 文件类型限制及单文件上传
- 转换 loading 与错误提示
- 格式化 JSON/XML 预览
- XML 复制和浏览器下载
- 错误、警告和统计信息展示
- 校验面板展示通过项、错误项和警告项数量，并按绿色、红色、黄色区分状态
- 人工校正文章结构并重新生成 XML
- 结构化 JSON 展示提取后的 figures，人工校正页可编辑图片 caption 和相对路径
- 结构化 JSON 展示 formulas，人工校正页可编辑公式内容并重新生成 `disp-formula`
- 响应式布局

## 后续扩展方向

- 增加结构化内容在线编辑与 XML 实时重建
- 展示原文与结构化结果的段落对照
- 提供图片预览、转换历史和批量上传
- 增加深色模式、国际化与可访问性审计
