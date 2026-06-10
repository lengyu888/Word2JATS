<script setup>
import { computed, ref } from 'vue'
import { DocumentAdd, MagicStick } from '@element-plus/icons-vue'

const props = defineProps({
  loading: Boolean,
})
const emit = defineEmits(['convert'])
const selectedFiles = ref([])

const fileLabel = computed(() => (
  selectedFiles.value.length
    ? `已选择 ${selectedFiles.value.length} 个文档`
    : '尚未选择文档'
))

function handleChange(uploadFile, uploadFiles) {
  selectedFiles.value = uploadFiles.map((item) => item.raw).filter(Boolean)
}

function handleRemove(uploadFile, uploadFiles) {
  selectedFiles.value = uploadFiles.map((item) => item.raw).filter(Boolean)
}

function convert() {
  if (selectedFiles.value.length) emit('convert', selectedFiles.value)
}
</script>

<template>
  <section class="upload-panel">
    <div class="step-number">01</div>
    <div class="upload-copy">
      <span class="eyebrow">SOURCE MANUSCRIPT</span>
      <h2>投递 Word 稿件</h2>
      <p>系统将识别文章元数据、正文层级、图表与参考文献，并构建可交换的 JATS XML。</p>
    </div>

    <el-upload
      drag
      action="#"
      accept=".docx"
      multiple
      :auto-upload="false"
      :on-change="handleChange"
      :on-remove="handleRemove"
      class="uploader"
    >
      <el-icon class="upload-icon"><DocumentAdd /></el-icon>
      <div class="drop-title">拖入一个或多个 .docx 文件</div>
      <div class="drop-subtitle">支持批量转换，或点击浏览本地稿件</div>
    </el-upload>

    <div class="action-row">
      <div class="file-label"><span></span>{{ fileLabel }}</div>
      <el-button
        type="primary"
        size="large"
        :loading="props.loading"
        :disabled="!selectedFiles.length"
        @click="convert"
      >
        <el-icon><MagicStick /></el-icon>
        开始批量转换
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.upload-panel { display: grid; grid-template-columns: 72px 1fr 1.15fr; gap: 28px; align-items: center; padding: 34px; background: #fffef9; border: 1px solid #d9d5c8; box-shadow: 8px 8px 0 #dce7e5; }
.step-number { align-self: start; font-family: Georgia, serif; font-size: 42px; color: #b8b3a5; line-height: 1; }
.eyebrow { color: #006d77; font-size: 11px; font-weight: 800; letter-spacing: .18em; }
h2 { margin: 8px 0 10px; font-family: Georgia, "Noto Serif SC", serif; font-size: 27px; color: #172522; }
p { margin: 0; max-width: 460px; color: #65706c; line-height: 1.8; font-size: 14px; }
.uploader :deep(.el-upload), .uploader :deep(.el-upload-dragger) { width: 100%; }
.uploader :deep(.el-upload-dragger) { padding: 26px; border: 1px dashed #86aaa5; border-radius: 2px; background: #f4f8f6; }
.uploader :deep(.el-upload-dragger:hover) { border-color: #006d77; background: #eef6f3; }
.upload-icon { font-size: 34px; color: #006d77; }
.drop-title { margin-top: 8px; color: #263b37; font-weight: 700; }
.drop-subtitle { margin-top: 4px; color: #89938f; font-size: 12px; }
.action-row { grid-column: 2 / 4; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #e6e1d5; padding-top: 20px; }
.file-label { display: flex; align-items: center; gap: 9px; color: #6b746f; font-size: 13px; }
.file-label span { width: 7px; height: 7px; border-radius: 50%; background: #e3a72f; }
.el-button { border-radius: 2px; font-weight: 700; letter-spacing: .04em; }
@media (max-width: 850px) {
  .upload-panel { grid-template-columns: 46px 1fr; }
  .uploader { grid-column: 1 / 3; }
  .action-row { grid-column: 1 / 3; }
}
</style>
