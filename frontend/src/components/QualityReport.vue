<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, default: () => ({ total_score: 0, scores: {}, issues: [], summary: {} }) },
})
const labels = {
  metadata_score: '元数据', structure_score: '正文结构', jats_schema_score: 'JATS Schema',
  figure_table_score: '图表', formula_score: '公式', reference_score: '参考文献', xref_score: '交叉引用',
}
const scoreRows = computed(() => Object.entries(props.report.scores || {}).map(([key, value]) => ({
  key, label: labels[key] || key, value,
})))
const issueTag = (level) => ({ error: 'danger', warning: 'warning', suggestion: 'info' }[level] || 'info')
</script>

<template>
  <div class="quality-report">
    <section class="score-hero">
      <div class="score-ring"><strong>{{ report.total_score ?? 0 }}</strong><span>/ 100</span></div>
      <div>
        <span class="eyebrow">DELIVERY READINESS</span>
        <h2>出版交付质量等级 {{ report.grade || '-' }}</h2>
        <p>综合评估元数据、正文结构、正式 JATS Schema、图表、公式、参考文献与交叉引用。</p>
      </div>
      <div class="summary">
        <b>{{ report.summary?.error_count || 0 }}</b><span>错误</span>
        <b>{{ report.summary?.warning_count || 0 }}</b><span>警告</span>
        <b>{{ report.summary?.suggestion_count || 0 }}</b><span>建议</span>
      </div>
    </section>
    <section class="score-grid">
      <div v-for="row in scoreRows" :key="row.key" class="score-item">
        <div><span>{{ row.label }}</span><b>{{ row.value }}</b></div>
        <el-progress :percentage="row.value" :show-text="false" :stroke-width="7" />
      </div>
    </section>
    <section class="issues">
      <div class="section-title"><span>LOCATED ISSUES</span><h3>错误定位与修复建议</h3></div>
      <el-table :data="report.issues || []" stripe empty-text="未发现需要定位的问题">
        <el-table-column label="级别" width="100">
          <template #default="{ row }"><el-tag :type="issueTag(row.level)">{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="130" />
        <el-table-column prop="location" label="定位" min-width="190" />
        <el-table-column prop="message" label="问题" min-width="240" />
        <el-table-column prop="suggestion" label="修复建议" min-width="280" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.quality-report { padding: 10px 4px; }.score-hero { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 28px; padding: 28px; color: #f7f2e7; background: #173c38; }
.score-ring { display: grid; place-items: center; width: 138px; height: 138px; border: 10px solid #e4a936; border-radius: 50%; }.score-ring strong { font: 50px Georgia, serif; line-height: 1; }.score-ring span { font-size: 11px; opacity: .7; }
.eyebrow, .section-title span { color: #e4a936; font-size: 10px; font-weight: 800; letter-spacing: .18em; }h2 { margin: 9px 0; font: 30px Georgia, "Noto Serif SC", serif; }.score-hero p { max-width: 620px; margin: 0; color: #c7d1cc; line-height: 1.8; font-size: 13px; }
.summary { display: grid; grid-template-columns: auto auto; gap: 5px 12px; }.summary b { color: #e4a936; font: 24px Georgia, serif; }.summary span { align-self: center; font-size: 11px; }
.score-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0; }.score-item { padding: 16px; border: 1px solid #ded9cd; background: #fffef9; }.score-item div { display: flex; justify-content: space-between; margin-bottom: 12px; }.score-item span { color: #64716c; font-size: 12px; }.score-item b { font: 22px Georgia, serif; }
.issues { padding: 20px; border: 1px solid #ded9cd; background: #fffef9; }.section-title h3 { margin: 7px 0 18px; font: 23px Georgia, "Noto Serif SC", serif; }@media (max-width: 900px) { .score-hero { grid-template-columns: 1fr; }.score-grid { grid-template-columns: 1fr 1fr; } }
</style>
