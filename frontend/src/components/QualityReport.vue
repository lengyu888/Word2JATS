<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, default: () => ({ total_score: 0, scores: {}, issues: [], summary: {} }) },
  formulas: { type: Array, default: () => [] },
})
const labels = {
  metadata_score: '元数据', structure_score: '正文结构', jats_schema_score: 'JATS Schema',
  figure_table_score: '图表', formula_score: '公式', reference_score: '参考文献', xref_score: '交叉引用',
}
const scoreRows = computed(() => Object.entries(props.report.scores || {}).map(([key, value]) => ({
  key, label: labels[key] || key, value,
})))
const issueTag = (level) => ({ error: 'danger', warning: 'warning', suggestion: 'info', need_review: 'primary' }[level] || 'info')
const formulaTag = (status) => ({ success: 'success', partial: 'warning', failed: 'danger' }[status] || 'info')
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
    <section class="evidence-grid">
      <article>
        <span>STRUCTURE EVIDENCE</span>
        <h3>图表绑定证据</h3>
        <div class="evidence-stats">
          <el-tag type="success">通过 {{ report.float_evidence_summary?.ok || 0 }}</el-tag>
          <el-tag type="warning">需复核 {{ report.float_evidence_summary?.need_review || 0 }}</el-tag>
          <el-tag type="danger">异常 {{ (report.float_evidence_summary?.warning || 0) + (report.float_evidence_summary?.error || 0) }}</el-tag>
        </div>
        <p>平均置信度：{{ report.float_evidence_summary?.average_confidence ?? '-' }}</p>
      </article>
      <article>
        <span>XREF TARGETS</span>
        <h3>交叉引用目标</h3>
        <div class="evidence-stats">
          <el-tag type="success">通过 {{ report.xref_summary?.passed || 0 }}</el-tag>
          <el-tag type="warning">需复核 {{ report.xref_summary?.need_review || 0 }}</el-tag>
          <el-tag type="info">父目标归一化 {{ report.xref_summary?.normalized || 0 }}</el-tag>
          <el-tag type="danger">缺失 {{ report.xref_summary?.missing || 0 }}</el-tag>
        </div>
        <p>仅对实际存在的 JATS ID 生成 xref，缺失目标保留为原文。</p>
      </article>
    </section>
    <section class="formula-overview">
      <div class="section-title"><span>FORMULA CONVERSION</span><h3>OMML 转换状态</h3></div>
      <div class="formula-stats">
        <div><b>{{ report.formula_summary?.total || 0 }}</b><span>公式总数</span></div>
        <div><b>{{ report.formula_summary?.mathml_success || 0 }}</b><span>MathML</span></div>
        <div><b>{{ report.formula_summary?.success || 0 }}</b><span>success</span></div>
        <div><b>{{ report.formula_summary?.partial || 0 }}</b><span>partial</span></div>
        <div><b>{{ report.formula_summary?.failed || 0 }}</b><span>failed</span></div>
      </div>
      <p v-if="report.formula_summary?.unsupported_features?.length" class="unsupported">
        不支持特性：{{ report.formula_summary.unsupported_features.join('、') }}
      </p>
      <div v-if="formulas.length" class="formula-list">
        <article v-for="formula in formulas" :key="formula.id">
          <header>
            <code>{{ formula.id }}</code>
            <el-tag :type="formulaTag(formula.conversion_status)">{{ formula.conversion_status || 'success' }}</el-tag>
          </header>
          <p><b>支持：</b>{{ formula.supported_features?.join('、') || '基础文本/未标记' }}</p>
          <p><b>不支持：</b>{{ formula.unsupported_features?.join('、') || '无' }}</p>
          <p v-for="(issue, index) in formula.issues || []" :key="index"><b>{{ issue.message }}</b> {{ issue.suggestion }}</p>
          <details><summary>LaTeX</summary><pre>{{ formula.latex || formula.content || '无' }}</pre></details>
          <details><summary>MathML</summary><pre>{{ formula.mathml || '无 MathML' }}</pre></details>
        </article>
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
.evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }.evidence-grid article { padding: 18px; border: 1px solid #ded9cd; background: #fffef9; }.evidence-grid article > span { color: #e4a936; font-size: 10px; font-weight: 800; letter-spacing: .15em; }.evidence-grid h3 { margin: 7px 0 14px; font: 20px Georgia, "Noto Serif SC", serif; }.evidence-grid p { margin: 12px 0 0; color: #64716c; font-size: 11px; }.evidence-stats { display: flex; flex-wrap: wrap; gap: 8px; }
.formula-overview, .issues { margin-top: 18px; padding: 20px; border: 1px solid #ded9cd; background: #fffef9; }.section-title h3 { margin: 7px 0 18px; font: 23px Georgia, "Noto Serif SC", serif; }
.formula-stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }.formula-stats div { display: grid; padding: 12px; background: #f4f1e8; text-align: center; }.formula-stats b { color: #006d77; font: 25px Georgia, serif; }.formula-stats span { margin-top: 4px; color: #73807b; font-size: 10px; }.unsupported { padding: 9px 12px; color: #9a671c; background: #fbf2df; font-size: 11px; }
.formula-list { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px; }.formula-list article { min-width: 0; padding: 13px; border: 1px solid #e3ded2; }.formula-list header { display: flex; justify-content: space-between; }.formula-list p { margin: 8px 0; color: #64716c; font-size: 11px; }.formula-list details { margin-top: 7px; }.formula-list summary { cursor: pointer; color: #006d77; font-size: 11px; }.formula-list pre { max-height: 150px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font: 10px/1.6 Consolas, monospace; }
@media (max-width: 900px) { .score-hero { grid-template-columns: 1fr; }.score-grid, .formula-stats, .formula-list, .evidence-grid { grid-template-columns: 1fr 1fr; } }
</style>
