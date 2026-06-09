<script setup>
import { ElMessage } from 'element-plus'

const props = defineProps({ xml: { type: String, required: true } })

async function copyXml() {
  await navigator.clipboard.writeText(props.xml)
  ElMessage.success('XML 已复制')
}

function downloadXml() {
  const blob = new Blob([props.xml], { type: 'application/xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'article.xml'
  anchor.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="xml-viewer">
    <div class="toolbar">
      <span>article.xml</span>
      <div>
        <el-button plain @click="copyXml">复制 XML</el-button>
        <el-button type="primary" @click="downloadXml">下载 XML</el-button>
      </div>
    </div>
    <pre>{{ xml }}</pre>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #e9eee9; border-bottom: 1px solid #ccd7d2; color: #53625d; font: 12px "Cascadia Code", Consolas, monospace; }
.toolbar .el-button { border-radius: 2px; }
pre { margin: 0; min-height: 430px; padding: 24px; overflow: auto; background: #12201e; color: #d5e9e1; font: 13px/1.75 "Cascadia Code", Consolas, monospace; }
</style>
