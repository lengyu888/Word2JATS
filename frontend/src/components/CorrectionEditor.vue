<script setup>
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'

const props = defineProps({
  article: { type: Object, required: true },
  loading: Boolean,
})
const emit = defineEmits(['regenerate'])

const form = reactive({
  title: '',
  abstract: '',
  keywords: [],
  authorsJson: '[]',
  affiliationsJson: '[]',
  sectionsJson: '[]',
  figuresJson: '[]',
  formulasJson: '[]',
  referencesJson: '[]',
})

function pretty(value) {
  return JSON.stringify(value || [], null, 2)
}

watch(
  () => props.article,
  (article) => {
    form.title = article.title || ''
    form.abstract = article.abstract || ''
    form.keywords = [...(article.keywords || [])]
    form.authorsJson = pretty(article.authors)
    form.affiliationsJson = pretty(article.affiliations)
    form.sectionsJson = pretty(article.sections)
    form.figuresJson = pretty(article.figures)
    form.formulasJson = pretty(article.formulas)
    form.referencesJson = pretty(article.references)
  },
  { immediate: true, deep: true },
)

function parseArray(label, value) {
  const parsed = JSON.parse(value)
  if (!Array.isArray(parsed)) throw new Error(`${label}必须是 JSON 数组`)
  return parsed
}

function regenerate() {
  try {
    const corrected = {
      ...structuredClone(props.article),
      title: form.title.trim(),
      abstract: form.abstract.trim(),
      keywords: form.keywords.map((item) => item.trim()).filter(Boolean),
      authors: parseArray('作者', form.authorsJson),
      affiliations: parseArray('单位', form.affiliationsJson),
      sections: parseArray('章节', form.sectionsJson),
      figures: parseArray('图片', form.figuresJson),
      formulas: parseArray('公式', form.formulasJson),
      references: parseArray('参考文献', form.referencesJson),
    }
    emit('regenerate', corrected)
  } catch (error) {
    ElMessage.error(`无法重新生成：${error.message}`)
  }
}
</script>

<template>
  <div class="correction-editor">
    <el-alert
      title="人工校正不会修改原始 Word 文件。提交后，系统将使用当前表单内容重新生成 XML。"
      type="info"
      show-icon
      :closable="false"
    />

    <el-form label-position="top" class="editor-form">
      <div class="basic-grid">
        <el-form-item label="文章标题">
          <el-input v-model="form.title" placeholder="请输入文章标题" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-select
            v-model="form.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词后按回车"
          />
        </el-form-item>
      </div>

      <el-form-item label="摘要">
        <el-input v-model="form.abstract" type="textarea" :rows="5" placeholder="请输入摘要" />
      </el-form-item>

      <div class="json-grid">
        <el-form-item label="作者 authors">
          <el-input v-model="form.authorsJson" type="textarea" :rows="9" />
        </el-form-item>
        <el-form-item label="单位 affiliations">
          <el-input v-model="form.affiliationsJson" type="textarea" :rows="9" />
        </el-form-item>
        <el-form-item label="章节 sections">
          <el-input v-model="form.sectionsJson" type="textarea" :rows="14" />
        </el-form-item>
        <el-form-item label="图片与图题 figures">
          <el-input v-model="form.figuresJson" type="textarea" :rows="14" />
        </el-form-item>
        <el-form-item label="数学公式 formulas">
          <el-input v-model="form.formulasJson" type="textarea" :rows="14" />
        </el-form-item>
        <el-form-item label="参考文献 references" class="wide">
          <el-input v-model="form.referencesJson" type="textarea" :rows="10" />
        </el-form-item>
      </div>

      <div class="editor-actions">
        <span>复杂字段必须保持合法 JSON 数组格式。</span>
        <el-button type="primary" size="large" :loading="loading" @click="regenerate">
          <el-icon><RefreshRight /></el-icon>
          重新生成 XML
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style scoped>
.correction-editor { padding: 8px 4px 4px; }
.editor-form { margin-top: 24px; }
.basic-grid, .json-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 22px; }
.json-grid { margin-top: 8px; }
.wide { grid-column: 1 / 3; }
.editor-actions { display: flex; align-items: center; justify-content: space-between; padding-top: 22px; border-top: 1px solid #ded9cd; }
.editor-actions span { color: #7c8883; font-size: 12px; }
.editor-actions .el-button { border-radius: 2px; font-weight: 700; }
:deep(.el-form-item__label) { color: #354943; font-weight: 700; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner), :deep(.el-select__wrapper) { border-radius: 2px; }
:deep(.el-textarea__inner) { font-family: "Cascadia Code", Consolas, monospace; line-height: 1.6; }
@media (max-width: 850px) {
  .basic-grid, .json-grid { grid-template-columns: 1fr; }
  .wide { grid-column: auto; }
  .editor-actions { align-items: stretch; flex-direction: column; gap: 14px; }
}
</style>
