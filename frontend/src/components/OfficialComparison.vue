<script setup>
import { computed } from 'vue'

const props = defineProps({
  comparison: { type: Object, default: () => ({}) },
})

const dimensionLabels = {
  metadata: '元数据',
  structure: '章节结构',
  figures_tables: '图表映射',
  formulas: '公式',
  references: '参考文献',
  xrefs: '交叉引用',
  compliance: 'XML 合规',
}

const metricLabels = {
  title: '标题', abstract: '摘要', keywords: '关键词', authors: '作者',
  affiliations: '单位', section_titles: '章节标题', section_levels: '章节层级',
  figures: '图片', tables: '表格', formulas: '公式', references: '参考文献',
  xrefs: '交叉引用', xml_well_formed: 'XML 可解析',
}

const dimensions = computed(() => Object.entries(props.comparison?.dimensions || {}).map(([key, value]) => ({
  key,
  label: dimensionLabels[key] || key,
  score: value.score ?? 0,
  weight: value.weight ?? 0,
  metrics: Object.entries(value.metrics || {}).map(([name, score]) => ({
    name: metricLabels[name] || name,
    score,
  })),
})))

function scoreType(score) {
  if (score >= 90) return 'success'
  if (score >= 80) return 'warning'
  return 'danger'
}

function shortValue(value) {
  if (Array.isArray(value)) return value.join('；')
  if (value === null || value === undefined || value === '') return '未提供'
  return String(value)
}
</script>

<template>
  <div class="official-comparison">
    <el-empty
      v-if="!props.comparison?.available"
      description="当前文档没有匹配的官方 XML，无法进行语义对比。"
    />
    <template v-else>
      <section class="hero-score">
        <div>
          <span>OFFICIAL JATS SEMANTIC COMPARISON</span>
          <h3>官方样例语义对比</h3>
          <p>按元数据、章节、图表、公式、参考文献和交叉引用评价，不以全局标签数量代替质量。</p>
        </div>
        <el-progress
          type="dashboard"
          :percentage="props.comparison.similarity_score || 0"
          :status="scoreType(props.comparison.similarity_score || 0)"
          :width="132"
        />
      </section>

      <div class="status-row">
        <el-tag :type="props.comparison.generated_xml_valid ? 'success' : 'danger'" effect="dark">
          生成 XML：{{ props.comparison.generated_xml_valid ? '可解析' : '不可解析' }}
        </el-tag>
        <el-tag :type="props.comparison.official_xml_valid ? 'success' : 'warning'">
          官方 XML：{{ props.comparison.official_xml_valid ? '可解析' : '容错解析' }}
        </el-tag>
        <el-tag type="info">指标版本 {{ props.comparison.metric_version || '1.0' }}</el-tag>
        <code>{{ props.comparison.official_xml }}</code>
      </div>

      <div class="dimension-grid">
        <el-card v-for="item in dimensions" :key="item.key" shadow="never">
          <div class="dimension-title">
            <b>{{ item.label }}</b>
            <el-tag :type="scoreType(item.score)">{{ item.score }} 分</el-tag>
          </div>
          <el-progress :percentage="item.score" :show-text="false" :status="scoreType(item.score)" />
          <div class="metric-list">
            <span v-for="metric in item.metrics" :key="metric.name">
              {{ metric.name }} <strong>{{ metric.score }}</strong>
            </span>
          </div>
        </el-card>
      </div>

      <h3>可恢复差异</h3>
      <el-alert
        v-if="!props.comparison.recoverable_differences?.length"
        title="未发现需要继续优化的可恢复结构差异。"
        type="success"
        show-icon
        :closable="false"
      />
      <el-table v-else :data="props.comparison.recoverable_differences" border>
        <el-table-column prop="metric" label="指标" width="130">
          <template #default="{ row }">{{ metricLabels[row.metric] || row.metric }}</template>
        </el-table-column>
        <el-table-column label="系统生成" min-width="220">
          <template #default="{ row }"><span class="clamp">{{ shortValue(row.generated) }}</span></template>
        </el-table-column>
        <el-table-column label="官方结果" min-width="220">
          <template #default="{ row }"><span class="clamp">{{ shortValue(row.official) }}</span></template>
        </el-table-column>
        <el-table-column prop="suggestion" label="优化建议" min-width="220" />
      </el-table>

      <h3>出版方补录差异</h3>
      <el-alert
        v-if="!props.comparison.publisher_enriched_differences?.length"
        title="未发现仅存在于官方成品中的出版方补录字段。"
        type="success"
        :closable="false"
      />
      <el-alert
        v-for="item in props.comparison.publisher_enriched_differences || []"
        :key="item.metric"
        :title="`${item.metric.toUpperCase()}：官方值 ${shortValue(item.official)}`"
        :description="item.suggestion"
        type="info"
        show-icon
        :closable="false"
        class="enriched-alert"
      />
    </template>
  </div>
</template>

<style scoped>
.official-comparison { padding: 10px 0 4px; }
.hero-score { display: flex; align-items: center; justify-content: space-between; padding: 22px 26px; border: 1px solid #d7d2c4; background: linear-gradient(135deg, #f6f4ea, #eef6f2); }
.hero-score span { color: #006d77; font-size: 10px; font-weight: 800; letter-spacing: .16em; }
.hero-score h3 { margin: 8px 0 5px; font: 600 26px Georgia, "Noto Serif SC", serif; }
.hero-score p { max-width: 680px; margin: 0; color: #68736e; }
.status-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 16px 0 20px; }
.status-row code { color: #68736e; font-size: 12px; }
.dimension-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.dimension-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.dimension-title b { color: #253b36; }
.metric-list { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 12px; color: #77817d; font-size: 12px; }
.metric-list strong { color: #253b36; }
h3 { margin: 24px 0 12px; color: #253b36; font: 18px Georgia, "Noto Serif SC", serif; }
.clamp { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; word-break: break-word; }
.enriched-alert { margin-bottom: 8px; }
@media (max-width: 1100px) { .dimension-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) {
  .hero-score { align-items: flex-start; gap: 16px; }
  .dimension-grid { grid-template-columns: 1fr; }
}
</style>
