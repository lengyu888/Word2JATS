<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  figures: { type: Array, default: () => [] },
  tables: { type: Array, default: () => [] },
  xml: { type: String, default: '' },
  qualityReport: { type: Object, default: () => ({ issues: [] }) },
})

const activeKind = ref('figures')
const imageDialog = ref(false)
const imageTarget = ref(null)
const fragmentDialog = ref(false)
const fragmentTitle = ref('')
const fragmentContent = ref('')
const brokenImages = ref(new Set())
const statusTypes = { ok: 'success', warning: 'warning', error: 'danger', need_review: 'primary' }
const statusLabels = { ok: '正常', warning: '警告', error: '错误', need_review: '待复核' }
const itemIds = computed(() => new Set([...props.figures, ...props.tables].map((item) => item.id)))
const unlocatedIssues = computed(() => (props.qualityReport?.issues || []).filter((issue) => (
  issue.module === 'figure_table'
  && ![...itemIds.value].some((id) => String(issue.location || '').includes(id))
)))

function markBroken(id) {
  brokenImages.value = new Set([...brokenImages.value, id])
}

function openImage(figure) {
  imageTarget.value = figure
  imageDialog.value = true
}

function showFragment(item, tag) {
  fragmentTitle.value = `${item.id} · ${tag}`
  try {
    const document = new DOMParser().parseFromString(props.xml, 'application/xml')
    const element = document.querySelector(`[id="${item.id}"]`)
    fragmentContent.value = element
      ? new XMLSerializer().serializeToString(element)
      : '未找到对应 XML 片段。'
  } catch {
    fragmentContent.value = '当前 XML 无法解析。'
  }
  fragmentDialog.value = true
}

const displayRows = (table) => (table.rows || []).slice(0, 10)
</script>

<template>
  <div class="visual-preview">
    <section class="visual-intro">
      <div><span>VISUAL ASSET REVIEW</span><h2>图片和表格可视化预览</h2><p>核对媒体、题注、章节归属、正文引用与 JATS 映射。</p></div>
      <div class="counts"><b>{{ figures.length }}</b><small>图片</small><b>{{ tables.length }}</b><small>表格</small></div>
    </section>

    <el-alert
      v-for="(issue, index) in unlocatedIssues"
      :key="index"
      class="global-issue"
      :title="`未定位图表问题：${issue.message}`"
      :description="issue.suggestion"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-tabs v-model="activeKind" class="asset-tabs">
      <el-tab-pane :label="`图片 Figures (${figures.length})`" name="figures">
        <el-empty v-if="!figures.length" description="当前文章没有识别到图片" />
        <div v-else class="figure-grid">
          <el-card v-for="figure in figures" :key="figure.id" class="asset-card" shadow="hover">
            <div
              v-if="figure.media_url && !brokenImages.has(figure.id)"
              class="image-frame"
              @click="openImage(figure)"
            >
              <img :src="figure.media_url" :alt="figure.caption || figure.id" @error="markBroken(figure.id)" />
              <span>点击查看大图</span>
            </div>
            <div v-else class="image-placeholder">图片不可预览<br /><small>{{ figure.filename || '未提取媒体文件' }}</small></div>
            <div class="card-title">
              <div><code>{{ figure.id }}</code><h3>{{ figure.caption || '未填写图题' }}</h3></div>
              <el-tag :type="statusTypes[figure.status] || 'info'">{{ statusLabels[figure.status] || figure.status }}</el-tag>
            </div>
            <dl>
              <dt>所属章节</dt><dd>{{ figure.section_title || '未定位章节' }}</dd>
              <dt>正文引用</dt><dd>{{ figure.referenced_by?.length || 0 }} 次</dd>
              <dt>媒体文件</dt><dd>{{ figure.filename || '-' }}</dd>
            </dl>
            <div v-if="figure.issues?.length" class="issues">
              <p v-for="(issue, index) in figure.issues" :key="index"><b>{{ issue.message }}</b><span>{{ issue.suggestion }}</span></p>
            </div>
            <el-button plain size="small" @click="showFragment(figure, 'fig')">查看 JATS 片段</el-button>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="`表格 Tables (${tables.length})`" name="tables">
        <el-empty v-if="!tables.length" description="当前文章没有识别到表格" />
        <div v-else class="table-list">
          <el-card v-for="table in tables" :key="table.id" class="asset-card table-card" shadow="hover">
            <div class="card-title">
              <div><code>{{ table.id }}</code><h3>{{ table.caption || '未填写表题' }}</h3></div>
              <el-tag :type="statusTypes[table.status] || 'info'">{{ statusLabels[table.status] || table.status }}</el-tag>
            </div>
            <dl>
              <dt>所属章节</dt><dd>{{ table.section_title || '未定位章节' }}</dd>
              <dt>规模</dt><dd>{{ table.row_count ?? table.rows?.length ?? 0 }} 行 × {{ table.column_count ?? 0 }} 列</dd>
              <dt>正文引用</dt><dd>{{ table.referenced_by?.length || 0 }} 次</dd>
            </dl>
            <div v-if="table.rows?.length" class="table-scroll">
              <table>
                <tbody>
                  <tr v-for="(row, rowIndex) in displayRows(table)" :key="rowIndex">
                    <component :is="rowIndex === 0 ? 'th' : 'td'" v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</component>
                  </tr>
                </tbody>
              </table>
              <small v-if="table.rows.length > 10">仅展示前 10 行，共 {{ table.rows.length }} 行。</small>
            </div>
            <el-alert v-else title="表格没有数据行" type="warning" show-icon :closable="false" />
            <div v-if="table.issues?.length" class="issues">
              <p v-for="(issue, index) in table.issues" :key="index"><b>{{ issue.message }}</b><span>{{ issue.suggestion }}</span></p>
            </div>
            <el-button plain size="small" @click="showFragment(table, 'table-wrap')">查看 JATS 片段</el-button>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="imageDialog" :title="imageTarget?.caption || imageTarget?.id" width="78%">
      <img v-if="imageTarget?.media_url" class="dialog-image" :src="imageTarget.media_url" :alt="imageTarget.caption" />
    </el-dialog>
    <el-dialog v-model="fragmentDialog" :title="fragmentTitle" width="76%">
      <pre class="xml-fragment">{{ fragmentContent }}</pre>
    </el-dialog>
  </div>
</template>

<style scoped>
.visual-preview { padding: 10px 4px; }.visual-intro { display: flex; justify-content: space-between; align-items: end; padding: 24px 28px; color: #f7f2e7; background: #173c38; }
.visual-intro span { color: #e4a936; font-size: 10px; font-weight: 800; letter-spacing: .18em; }.visual-intro h2 { margin: 8px 0; font: 28px Georgia, "Noto Serif SC", serif; }.visual-intro p { margin: 0; color: #c7d1cc; font-size: 12px; }
.counts { display: grid; grid-template-columns: auto auto; gap: 2px 10px; align-items: center; }.counts b { color: #e4a936; font: 30px Georgia, serif; }.counts small { color: #c7d1cc; }.global-issue { margin-top: 12px; }.asset-tabs { margin-top: 16px; }
.figure-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.table-list { display: grid; gap: 18px; }.asset-card { border-color: #ded9cd; background: #fffef9; }
.image-frame, .image-placeholder { display: grid; place-items: center; height: 220px; margin: -20px -20px 18px; background: #ece9df; overflow: hidden; }.image-frame { position: relative; cursor: zoom-in; }.image-frame img { width: 100%; height: 100%; object-fit: contain; }.image-frame span { position: absolute; right: 8px; bottom: 8px; padding: 5px 8px; color: white; background: rgba(23,60,56,.78); font-size: 10px; }.image-placeholder { color: #87918d; text-align: center; line-height: 1.8; }.image-placeholder small { font-size: 10px; }
.card-title { display: flex; justify-content: space-between; gap: 12px; align-items: start; }.card-title code { color: #007680; font-size: 11px; }.card-title h3 { margin: 7px 0 12px; font: 18px Georgia, "Noto Serif SC", serif; }
dl { display: grid; grid-template-columns: 76px 1fr; gap: 7px 10px; margin: 0 0 14px; font-size: 11px; }dt { color: #8a948f; }dd { margin: 0; overflow-wrap: anywhere; }.issues { display: grid; gap: 7px; margin: 12px 0; }.issues p { margin: 0; padding: 9px; border-left: 3px solid #e4a936; background: #fbf4e5; font-size: 11px; }.issues b, .issues span { display: block; }.issues span { margin-top: 4px; color: #78837e; }
.table-scroll { margin: 14px 0; overflow-x: auto; }.table-scroll table { width: 100%; border-collapse: collapse; font-size: 11px; }.table-scroll th, .table-scroll td { padding: 8px 10px; border: 1px solid #ded9cd; text-align: left; }.table-scroll th { background: #e9f1ee; }.table-scroll small { display: block; margin-top: 7px; color: #8a948f; }
.dialog-image { display: block; max-width: 100%; max-height: 72vh; margin: auto; }.xml-fragment { max-height: 65vh; margin: 0; padding: 16px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; background: #172522; color: #e7efe9; font: 12px/1.7 Consolas, monospace; }
@media (max-width: 1000px) { .figure-grid { grid-template-columns: 1fr 1fr; } }@media (max-width: 650px) { .figure-grid { grid-template-columns: 1fr; }.visual-intro { align-items: start; gap: 20px; } }
</style>
