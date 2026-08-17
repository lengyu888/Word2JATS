<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import UploadPanel from './components/UploadPanel.vue'
import JsonViewer from './components/JsonViewer.vue'
import XmlViewer from './components/XmlViewer.vue'
import ValidationPanel from './components/ValidationPanel.vue'
import CorrectionEditor from './components/CorrectionEditor.vue'
import BatchResults from './components/BatchResults.vue'
import QualityReport from './components/QualityReport.vue'
import FlowMappingViewer from './components/FlowMappingViewer.vue'
import FigureTablePreview from './components/FigureTablePreview.vue'
import OfficialComparison from './components/OfficialComparison.vue'
import { batchConvertDocuments, exportPackage, generateXml, getDemoDocuments, getProfiles } from './api/convert'

const loading = ref(false)
const regenerating = ref(false)
const result = ref(null)
const batchResults = ref([])
const activeTab = ref('json')
const profiles = ref([])
const exportStatuses = ref({})
let batchSequence = 0
const sectionCount = computed(() => result.value?.article.sections.length || 0)
const referenceCount = computed(() => result.value?.article.references.length || 0)

function resultKey(item) {
  return item?.conversion_id || item?.client_key || ''
}

onMounted(async () => {
  try {
    profiles.value = await getProfiles()
  } catch {
    profiles.value = [{ id: 'default', label: 'Default prototype', lang: 'zh' }]
  }
})

async function convert(files, profile) {
  loading.value = true
  try {
    const batch = await batchConvertDocuments(files, profile)
    batchSequence += 1
    exportStatuses.value = {}
    batchResults.value = batch.results.map((item, index) => ({
      ...item,
      client_key: item.conversion_id || `batch-${batchSequence}-${index}`,
    }))
    result.value = batchResults.value.find((item) => item.status === 'success') || null
    activeTab.value = 'json'
    ElMessage.success(`批量转换完成：${batch.results.filter((item) => item.status === 'success').length}/${batch.results.length} 成功`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '转换失败，请检查后端服务和文档格式')
  } finally {
    loading.value = false
  }
}

async function loadDemo(profile = 'default') {
  loading.value = true
  try {
    const files = await getDemoDocuments()
    await convert(files, profile)
    ElMessage.success(`${files.length} 篇官方样例已加载并完成批量转换`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '演示数据加载失败')
  } finally {
    loading.value = false
  }
}

function selectResult(item) {
  result.value = item
  activeTab.value = 'json'
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function downloadXml(item) {
  downloadBlob(
    new Blob([item.xml], { type: 'application/xml;charset=utf-8' }),
    `${item.filename.replace(/\.docx$/i, '') || 'article'}.xml`,
  )
}

async function downloadPackage(item) {
  const key = resultKey(item)
  exportStatuses.value[key] = '生成中'
  try {
    const blob = await exportPackage({
      filename: item.filename,
      article: item.article,
      xml: item.xml,
      media_paths: item.media_paths || [],
      validation: item.validation,
      quality_report: item.quality_report,
    })
    downloadBlob(blob, `${item.filename.replace(/\.docx$/i, '') || 'article'}-word2jats.zip`)
    exportStatuses.value[key] = '已导出'
  } catch (error) {
    exportStatuses.value[key] = '导出失败'
    ElMessage.error(error.response?.data?.detail || 'ZIP 结果包生成失败')
  }
}

async function regenerate(article) {
  regenerating.value = true
  try {
    const generated = await generateXml(article)
    result.value = {
      ...result.value,
      article: generated.article || article,
      xml: generated.xml,
      validation: generated.validation,
      quality_report: generated.quality_report,
      processing_stats: generated.processing_stats,
    }
    const selectedKey = resultKey(result.value)
    batchResults.value = batchResults.value.map((item) => (
      resultKey(item) === selectedKey ? result.value : item
    ))
    activeTab.value = 'xml'
    ElMessage.success('XML 已根据人工校正内容重新生成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '重新生成失败，请检查校正内容')
  } finally {
    regenerating.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <header class="masthead">
      <div class="brand-mark">W<span>2</span>J</div>
      <div>
        <span class="kicker">STRUCTURED PUBLISHING LAB · MVP 0.1</span>
        <h1>Word2JATS<span>：</span>学术期刊 Word 文档智能结构化转换系统</h1>
      </div>
      <div class="system-state"><i></i> RULE ENGINE ONLINE</div>
    </header>

    <main>
      <section class="hero">
        <div>
          <span class="hero-label">FROM MANUSCRIPT TO MACHINE-READABLE ARTICLE</span>
          <h2>让每一篇论文<br /><em>拥有清晰结构。</em></h2>
        </div>
        <p>无需商业 API，使用可解释的规则算法从 Word 稿件中提取出版语义，并生成面向 JATS 的 XML。</p>
      </section>

      <section class="capability-grid">
        <article v-for="(card, index) in [
          ['01', 'Word 文档流解析', '按 document.xml 真实顺序恢复段落、图片、表格与公式。'],
          ['02', 'JATS Schema 校验', '使用本地正式 JATS Publishing 1.3 DTD 定位交付问题。'],
          ['03', 'OMML → MathML', '保留原生公式并生成 MathML、LaTeX 与文本回退。'],
          ['04', '图表公式引用恢复', '将正文引用转换为可校验的 JATS xref。'],
          ['05', '批量转换与 ZIP 交付', '逐篇质量评分并交付 XML、JSON、报告和媒体资源。'],
        ]" :key="card[0]">
          <span>{{ card[0] }}</span><h3>{{ card[1] }}</h3><p>{{ card[2] }}</p>
        </article>
      </section>

      <UploadPanel :loading="loading" :profiles="profiles" @convert="convert" @demo="loadDemo" />
      <BatchResults
        v-if="batchResults.length"
        :results="batchResults"
        :export-statuses="exportStatuses"
        @select="selectResult"
        @download-xml="downloadXml"
        @download-package="downloadPackage"
      />

      <section v-if="result" class="results">
        <div class="result-heading">
          <div>
            <span class="section-index">02 / CONVERSION OUTPUT</span>
            <h2>结构化产物审阅</h2>
          </div>
          <div class="metrics">
            <div><b>{{ sectionCount }}</b><span>章节</span></div>
            <div><b>{{ referenceCount }}</b><span>参考文献</span></div>
            <div><b>{{ result.validation.errors.length }}</b><span>错误</span></div>
          </div>
        </div>
        <el-tabs v-model="activeTab" class="output-tabs">
          <el-tab-pane label="人工校正" name="correction">
            <CorrectionEditor
              :article="result.article"
              :loading="regenerating"
              @regenerate="regenerate"
            />
          </el-tab-pane>
          <el-tab-pane label="结构化 JSON" name="json"><JsonViewer :data="result.article" /></el-tab-pane>
          <el-tab-pane label="文档流对照" name="flow">
            <FlowMappingViewer :flow="result.article.document_flow_view || []" :xml="result.xml" />
          </el-tab-pane>
          <el-tab-pane label="图表预览" name="visual">
            <FigureTablePreview
              :figures="result.article.figures || []"
              :tables="result.article.tables || []"
              :xml="result.xml"
              :quality-report="result.quality_report"
            />
          </el-tab-pane>
          <el-tab-pane label="JATS XML" name="xml"><XmlViewer :xml="result.xml" /></el-tab-pane>
          <el-tab-pane label="官方对比" name="official">
            <OfficialComparison :comparison="result.official_comparison || {}" />
          </el-tab-pane>
          <el-tab-pane label="校验结果" name="validation"><ValidationPanel :validation="result.validation" /></el-tab-pane>
          <el-tab-pane label="质量报告" name="quality">
            <QualityReport :report="result.quality_report" :formulas="result.article.formulas || []" />
          </el-tab-pane>
        </el-tabs>
      </section>

      <section v-else class="empty-state">
        <span>02</span>
        <p>转换产物将在这里展开：结构化 JSON、JATS XML 与基础校验结果。</p>
      </section>
    </main>
    <footer>WORD2JATS · A RULE-BASED PROTOTYPE FOR ACADEMIC PUBLISHING</footer>
  </div>
</template>

<style>
:root { --ink: #172522; --paper: #f3f0e6; --blue: #006d77; --line: #d7d2c4; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .28; background-image: radial-gradient(#9b998f 0.55px, transparent 0.55px); background-size: 5px 5px; }
.page-shell { position: relative; max-width: 1440px; min-height: 100vh; margin: auto; padding: 0 5vw; }
.masthead { display: grid; grid-template-columns: 72px 1fr auto; align-items: center; gap: 18px; min-height: 94px; border-bottom: 1px solid var(--ink); }
.brand-mark { font: bold 32px Georgia, serif; letter-spacing: -.08em; }.brand-mark span { color: #d28d24; }
.kicker, .hero-label, .section-index { color: var(--blue); font-size: 10px; font-weight: 800; letter-spacing: .18em; }
.masthead h1 { margin: 6px 0 0; font-family: Georgia, "Noto Serif SC", serif; font-size: clamp(16px, 2vw, 24px); font-weight: 600; }.masthead h1 span { color: #d28d24; }
.system-state { padding: 8px 10px; border: 1px solid #9ba6a2; color: #53625d; font-size: 9px; letter-spacing: .14em; }.system-state i { display: inline-block; width: 6px; height: 6px; margin-right: 6px; border-radius: 50%; background: #2d9f78; }
main { padding: 60px 0 80px; }
.hero { display: grid; grid-template-columns: 1.3fr .7fr; align-items: end; gap: 50px; margin-bottom: 42px; }
.hero h2 { margin: 14px 0 0; font: 600 clamp(40px, 6vw, 78px)/1.12 Georgia, "Noto Serif SC", serif; letter-spacing: -.045em; }
.hero h2 em { color: var(--blue); font-weight: inherit; }.hero p { margin: 0 0 8px; padding-left: 18px; border-left: 2px solid #d28d24; color: #66716d; line-height: 1.9; font-size: 14px; }
.capability-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: -8px 0 30px; }.capability-grid article { min-height: 150px; padding: 18px; border: 1px solid var(--line); background: rgba(255,254,249,.72); transition: transform .2s, background .2s; }.capability-grid article:hover { transform: translateY(-4px); background: #fffef9; }.capability-grid span { color: #d28d24; font: 17px Georgia, serif; }.capability-grid h3 { margin: 18px 0 8px; font: 16px Georgia, "Noto Serif SC", serif; }.capability-grid p { margin: 0; color: #75807c; font-size: 11px; line-height: 1.7; }
.results { margin-top: 64px; }
.result-heading { display: flex; align-items: end; justify-content: space-between; margin-bottom: 20px; }
.result-heading h2 { margin: 9px 0 0; font: 600 30px Georgia, "Noto Serif SC", serif; }
.metrics { display: flex; gap: 34px; }.metrics div { display: grid; text-align: center; }.metrics b { font: 28px Georgia, serif; }.metrics span { margin-top: 4px; color: #7d8883; font-size: 11px; }
.output-tabs { padding: 0 22px 22px; background: #fffef9; border: 1px solid var(--line); }
.output-tabs .el-tabs__item { height: 58px; font-weight: 700; }.output-tabs .el-tabs__item.is-active { color: var(--blue); }.output-tabs .el-tabs__active-bar { background: var(--blue); }
.empty-state { display: flex; align-items: center; gap: 24px; margin-top: 64px; padding: 32px; border: 1px dashed #b8b5aa; color: #8a918d; }.empty-state span { font: 40px Georgia, serif; color: #beb9ab; }.empty-state p { margin: 0; font-size: 13px; }
footer { padding: 20px 0 32px; border-top: 1px solid var(--line); color: #89908d; font-size: 9px; letter-spacing: .17em; }
@media (max-width: 850px) {
  .page-shell { padding: 0 18px; }.masthead { grid-template-columns: 50px 1fr; }.system-state { display: none; }.hero { grid-template-columns: 1fr; }.hero h2 { font-size: 45px; }.capability-grid { grid-template-columns: 1fr 1fr; }.result-heading { align-items: start; flex-direction: column; gap: 20px; }.metrics { width: 100%; justify-content: space-between; }
}
</style>
