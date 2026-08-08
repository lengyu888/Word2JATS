<script setup>
defineProps({
  results: { type: Array, required: true },
  exportStatuses: { type: Object, default: () => ({}) },
})
defineEmits(['select', 'download-xml', 'download-package'])

function formatElapsed(seconds) {
  if (seconds === undefined || seconds === null) return '-'
  return `${Number(seconds).toFixed(2)}s`
}
</script>

<template>
  <section class="batch-results">
    <div class="batch-heading">
      <div>
        <span>BATCH CONVERSION</span>
        <h2>批量转换列表</h2>
      </div>
      <strong>{{ results.filter((item) => item.status === 'success').length }} / {{ results.length }} 成功</strong>
    </div>

    <div class="result-list">
      <div v-for="(item, index) in results" :key="`${item.filename}-${index}`" class="result-row">
        <div class="file-info">
          <el-tag :type="item.status === 'success' ? 'success' : 'danger'" effect="dark">
            {{ item.status === 'success' ? '成功' : '失败' }}
          </el-tag>
          <div>
            <b>{{ item.filename }}</b>
            <small v-if="item.status === 'success'">{{ item.article?.title || '未识别标题' }}</small>
            <small v-else>{{ item.error }}</small>
          </div>
        </div>
        <div class="counts">
          <span>质量分 <b>{{ item.quality_report?.total_score ?? '-' }}</b></span>
          <span>官方相似度 <b>{{ item.official_comparison?.available ? `${item.official_comparison.similarity_score}%` : '-' }}</b></span>
          <span>警告 <b>{{ item.validation?.warnings?.length || 0 }}</b></span>
          <span>错误 <b>{{ item.validation?.errors?.length || 0 }}</b></span>
          <span>耗时 <b>{{ formatElapsed(item.processing_stats?.elapsed_seconds) }}</b></span>
          <span>节点 <b>{{ item.processing_stats?.source_node_count ?? '-' }}</b></span>
          <span>导出 <b>{{ exportStatuses[item.filename] || '待导出' }}</b></span>
        </div>
        <div class="actions">
          <el-button :disabled="item.status !== 'success'" @click="$emit('select', item)">查看详情</el-button>
          <el-button :disabled="item.status !== 'success'" @click="$emit('download-xml', item)">下载 XML</el-button>
          <el-button type="primary" :loading="exportStatuses[item.filename] === '生成中'" :disabled="item.status !== 'success'" @click="$emit('download-package', item)">
            下载 ZIP
          </el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.batch-results { margin-top: 42px; padding: 24px; border: 1px solid #d7d2c4; background: #fffef9; }
.batch-heading { display: flex; align-items: end; justify-content: space-between; margin-bottom: 18px; }
.batch-heading span { color: #006d77; font-size: 10px; font-weight: 800; letter-spacing: .18em; }
.batch-heading h2 { margin: 7px 0 0; font: 600 25px Georgia, "Noto Serif SC", serif; }
.batch-heading strong { color: #006d77; font-size: 13px; }
.result-list { display: grid; gap: 10px; }
.result-row { display: grid; grid-template-columns: minmax(260px, 1fr) auto auto; align-items: center; gap: 22px; padding: 15px; border: 1px solid #e2ddd1; background: #faf9f3; }
.file-info { display: flex; align-items: center; gap: 13px; min-width: 0; }
.file-info div { display: grid; gap: 4px; min-width: 0; }
.file-info b, .file-info small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-info small { color: #7a8580; }
.counts { display: flex; gap: 14px; color: #727d78; font-size: 12px; }
.counts b { color: #253b36; }
.actions { display: flex; gap: 8px; }
@media (max-width: 1000px) {
  .result-row { grid-template-columns: 1fr; }
  .actions { flex-wrap: wrap; }
}
</style>
