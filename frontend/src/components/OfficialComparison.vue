<script setup>
const props = defineProps({
  comparison: { type: Object, default: () => ({}) },
})

function percent(value) {
  return Number.isFinite(Number(value)) ? `${Math.round(Number(value))}%` : '-'
}
</script>

<template>
  <div class="official-comparison">
    <el-empty v-if="!props.comparison?.available" description="当前文档没有匹配的官方 XML 结果，无法对比。" />
    <template v-else>
      <div class="summary-grid">
        <el-card shadow="never">
          <span>结构相似度</span>
          <b>{{ percent(props.comparison.similarity_score) }}</b>
        </el-card>
        <el-card shadow="never">
          <span>生成 XML</span>
          <el-tag :type="props.comparison.generated_xml_valid ? 'success' : 'danger'">
            {{ props.comparison.generated_xml_valid ? '可解析' : '不可解析' }}
          </el-tag>
        </el-card>
        <el-card shadow="never">
          <span>官方 XML</span>
          <el-tag :type="props.comparison.official_xml_valid ? 'success' : 'warning'">
            {{ props.comparison.official_xml_valid ? '可解析' : '已容错解析' }}
          </el-tag>
        </el-card>
        <el-card shadow="never">
          <span>官方结果</span>
          <b class="xml-name">{{ props.comparison.official_xml }}</b>
        </el-card>
      </div>

      <h3>关键 JATS 标签数量对比</h3>
      <el-table :data="Object.keys(props.comparison.counts?.generated || {}).map((key) => ({
        tag: key,
        generated: props.comparison.counts.generated[key],
        official: props.comparison.counts.official?.[key] ?? 0,
      }))" border>
        <el-table-column prop="tag" label="JATS 标签" min-width="160" />
        <el-table-column prop="generated" label="系统生成" width="120" />
        <el-table-column prop="official" label="官方结果" width="120" />
      </el-table>

      <h3>差异提示</h3>
      <el-alert
        v-if="!props.comparison.differences?.length"
        title="关键结构数量与官方结果一致。"
        type="success"
        show-icon
        :closable="false"
      />
      <el-table v-else :data="props.comparison.differences" border>
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'error' ? 'danger' : 'warning'">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric" label="指标" width="140" />
        <el-table-column prop="generated" label="系统生成" width="110" />
        <el-table-column prop="official" label="官方结果" width="110" />
        <el-table-column prop="message" label="说明" min-width="280" />
      </el-table>
    </template>
  </div>
</template>

<style scoped>
.official-comparison { padding: 10px 0 4px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.summary-grid :deep(.el-card__body) { display: grid; gap: 8px; min-height: 104px; }
.summary-grid span { color: #7a8580; font-size: 12px; font-weight: 700; }
.summary-grid b { color: #253b36; font: 28px Georgia, serif; }
.summary-grid .xml-name { font: 13px "Cascadia Code", Consolas, monospace; word-break: break-all; }
h3 { margin: 22px 0 12px; color: #253b36; font: 18px Georgia, "Noto Serif SC", serif; }
@media (max-width: 900px) {
  .summary-grid { grid-template-columns: 1fr 1fr; }
}
</style>
