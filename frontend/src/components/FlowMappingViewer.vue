<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  flow: { type: Array, default: () => [] },
  xml: { type: String, default: '' },
})

const activeFilter = ref('all')
const selected = ref(null)
const filters = [
  ['all', '全部'],
  ['metadata', '元数据'],
  ['body', '正文'],
  ['visual', '图表'],
  ['formula', '公式'],
  ['reference', '参考文献'],
  ['issues', '有问题节点'],
]
const groups = {
  metadata: ['title', 'author', 'affiliation', 'abstract', 'keyword'],
  body: ['heading', 'paragraph', 'xref_paragraph', 'list'],
  visual: ['figure', 'figure_caption', 'table', 'table_caption'],
  formula: ['formula'],
  reference: ['reference'],
}
const statusTypes = { ok: 'success', warning: 'warning', error: 'danger', need_review: 'primary' }
const statusLabels = { ok: '正常', warning: '警告', error: '错误', need_review: '待复核' }
const nodeLabels = {
  title: '标题', author: '作者', affiliation: '单位', abstract: '摘要', keyword: '关键词',
  heading: '章节标题', paragraph: '正文段落', xref_paragraph: '交叉引用段落', list: '列表',
  figure: '图片', figure_caption: '图题', table: '表格', table_caption: '表题',
  formula: '公式', reference: '参考文献', unknown: '未识别',
}

const filtered = computed(() => {
  if (activeFilter.value === 'all') return props.flow
  if (activeFilter.value === 'issues') return props.flow.filter((item) => item.status !== 'ok')
  return props.flow.filter((item) => groups[activeFilter.value]?.includes(item.node_type))
})

const xmlFragment = computed(() => {
  if (!selected.value || !props.xml) return ''
  try {
    const document = new DOMParser().parseFromString(props.xml, 'application/xml')
    let element = selected.value.target_id
      ? document.querySelector(`[id="${selected.value.target_id}"]`)
      : null
    if (!element) {
      const rawTag = selected.value.jats_tag?.split('/').at(-1)?.replace(/^.*:/, '')
      element = rawTag && !rawTag.includes(' ') ? document.getElementsByTagName(rawTag)[0] : null
    }
    return element ? new XMLSerializer().serializeToString(element) : '未能从当前 XML 精确定位片段。'
  } catch {
    return '当前 XML 无法解析。'
  }
})

watch(
  () => props.flow,
  (flow) => { selected.value = flow?.[0] || null },
  { immediate: true },
)
</script>

<template>
  <div class="flow-viewer">
    <section class="flow-intro">
      <div>
        <span>DOCX FLOW → JATS</span>
        <h2>原文节点流 — JATS 标签对照</h2>
        <p>按 Word 文档真实顺序展示识别类型、章节归属、目标标签与质量问题。</p>
      </div>
      <strong>{{ flow.length }}<small> 个节点</small></strong>
    </section>

    <div class="filters">
      <el-radio-group v-model="activeFilter" size="small">
        <el-radio-button v-for="[value, label] in filters" :key="value" :value="value">
          {{ label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <el-table
      :data="filtered"
      stripe
      highlight-current-row
      empty-text="当前筛选条件下没有节点"
      @row-click="selected = $event"
    >
      <el-table-column prop="index" label="序号" width="65" />
      <el-table-column prop="preview" label="原文预览" min-width="230" show-overflow-tooltip />
      <el-table-column label="节点类型" width="125">
        <template #default="{ row }">{{ nodeLabels[row.node_type] || row.node_type }}</template>
      </el-table-column>
      <el-table-column prop="jats_tag" label="JATS 标签" min-width="145" />
      <el-table-column prop="section_title" label="所属章节" min-width="120" />
      <el-table-column prop="target_id" label="目标 ID" width="90" />
      <el-table-column label="置信度" width="105">
        <template #default="{ row }">{{ Math.round(row.confidence * 100) }}%</template>
      </el-table-column>
      <el-table-column label="状态" width="95">
        <template #default="{ row }">
          <el-tag :type="statusTypes[row.status] || 'info'" effect="light">
            {{ statusLabels[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="问题/建议" min-width="220">
        <template #default="{ row }">
          <span v-if="row.issues?.length">{{ row.issues[0].message }}：{{ row.issues[0].suggestion }}</span>
          <span v-else class="muted">无</span>
        </template>
      </el-table-column>
    </el-table>

    <section v-if="selected" class="detail-card">
      <div class="detail-heading">
        <div><span>NODE {{ selected.index }}</span><h3>{{ nodeLabels[selected.node_type] || selected.node_type }}</h3></div>
        <el-tag :type="statusTypes[selected.status] || 'info'">{{ statusLabels[selected.status] || selected.status }}</el-tag>
      </div>
      <div class="detail-grid">
        <article><label>原文完整内容</label><pre>{{ selected.text || '无文本内容' }}</pre></article>
        <article><label>JATS 路径</label><code>{{ selected.jats_path || '尚未定位' }}</code></article>
        <article class="wide"><label>关联 XML 片段</label><pre>{{ xmlFragment }}</pre></article>
        <article class="wide">
          <label>问题与修复建议</label>
          <div v-if="selected.issues?.length" class="issue-list">
            <el-alert
              v-for="(issue, index) in selected.issues"
              :key="index"
              :title="issue.message"
              :description="issue.suggestion"
              :type="issue.level === 'error' ? 'error' : issue.level === 'warning' ? 'warning' : 'info'"
              show-icon
              :closable="false"
            />
          </div>
          <p v-else class="muted">该节点暂未发现映射问题。</p>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.flow-viewer { padding: 10px 4px; }
.flow-intro { display: flex; justify-content: space-between; align-items: end; padding: 24px 28px; color: #f7f2e7; background: #173c38; }
.flow-intro span, .detail-heading span { color: #e4a936; font-size: 10px; font-weight: 800; letter-spacing: .18em; }
.flow-intro h2 { margin: 8px 0; font: 28px Georgia, "Noto Serif SC", serif; }.flow-intro p { margin: 0; color: #c7d1cc; font-size: 12px; }
.flow-intro strong { color: #e4a936; font: 42px Georgia, serif; }.flow-intro small { color: #c7d1cc; font: 11px "Microsoft YaHei"; }
.filters { padding: 16px 0; overflow-x: auto; }
.detail-card { margin-top: 18px; padding: 22px; border: 1px solid #ded9cd; background: #fffef9; }
.detail-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }.detail-heading h3 { margin: 5px 0 0; font: 22px Georgia, "Noto Serif SC", serif; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }.detail-grid article { min-width: 0; padding: 15px; border: 1px solid #e5e0d5; background: #f8f6ef; }.detail-grid .wide { grid-column: 1 / -1; }
label { display: block; margin-bottom: 9px; color: #62716c; font-size: 11px; font-weight: 700; }pre, code { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; color: #33443f; font: 12px/1.7 Consolas, monospace; }
.issue-list { display: grid; gap: 8px; }.muted { color: #98a09d; font-size: 12px; }
@media (max-width: 850px) { .flow-intro { align-items: start; gap: 20px; }.detail-grid { grid-template-columns: 1fr; }.detail-grid .wide { grid-column: auto; } }
</style>
