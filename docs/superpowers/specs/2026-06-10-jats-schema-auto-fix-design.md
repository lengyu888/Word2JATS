# JATS Schema 自动修复设计

## 目标

在不编造出版数据、不删除有效内容的前提下，根据正式 JATS Schema 错误执行白名单自动修复，并将已修复项与仍需人工处理的问题返回给用户。

## 架构

新增 `JatsAutoFixer`，接收生成 XML、首次 Schema 校验结果和 Schema 校验器。修复器仅识别确定性错误，修改 XML 后重新校验，最多执行两轮。转换与人工重新生成接口在业务校验前运行自动修复闭环，保持原有接口字段兼容。

## 首期修复规则

- 将 `graphic/@href` 转换为正式 JATS 要求的 `graphic/@xlink:href`。
- 根据 DTD 内容模型重新排列 `journal-meta` 已有子节点。
- 清理值为空且 Schema 明确不接受的普通属性。
- 修复重复 XML `id`，并同步更新对应 `xref/@rid`。

自动修复不会补写 ISSN、DOI、ORCID、作者、单位或出版日期等无法可靠推断的真实出版数据。

## 返回结构

`validation.auto_fix` 包含：

- `attempted`
- `applied_fixes`
- `remaining_schema_errors`
- `before_schema_error_count`
- `after_schema_error_count`

每条修复记录包含 `code`、`location` 和 `message`。

## 前端

校验面板新增“自动修复记录”和“仍需人工处理”区域。正式 Schema 状态仍以修复后的最终校验结果为准。

## 测试

- 单元测试覆盖 xlink、节点顺序、重复 ID 和不编造元数据。
- API 测试覆盖兼容返回结构。
- 全量 pytest、前端构建、正式 DTD 演示稿转换与 Docker 链路验证。

