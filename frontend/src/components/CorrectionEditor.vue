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
  doi: '',
  articleType: 'research-article',
  lang: 'zh',
  journalTitle: '',
  journalId: '',
  issn: '',
  publisherName: '',
  subject: '',
  pubYear: '',
  pubMonth: '',
  pubDay: '',
  abstract: '',
  keywords: [],
  authorsJson: '[]',
  affiliationsJson: '[]',
  sectionsJson: '[]',
  figuresJson: '[]',
  tablesJson: '[]',
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
    form.doi = article.doi || ''
    form.articleType = article.article_type || 'research-article'
    form.lang = article.lang || 'zh'
    form.journalTitle = article.journal_title || ''
    form.journalId = article.journal_id || ''
    form.issn = article.issn || ''
    form.publisherName = article.publisher_name || ''
    form.subject = article.subject || ''
    form.pubYear = article.pub_year || ''
    form.pubMonth = article.pub_month || ''
    form.pubDay = article.pub_day || ''
    form.abstract = article.abstract || ''
    form.keywords = [...(article.keywords || [])]
    form.authorsJson = pretty(article.authors)
    form.affiliationsJson = pretty(article.affiliations)
    form.sectionsJson = pretty(article.sections)
    form.figuresJson = pretty(article.figures)
    form.tablesJson = pretty(article.tables)
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

function cloneArticle(article) {
  return JSON.parse(JSON.stringify(article))
}

function regenerate() {
  try {
    const corrected = {
      ...cloneArticle(props.article),
      title: form.title.trim(),
      doi: form.doi.trim(),
      article_type: form.articleType.trim() || 'research-article',
      lang: form.lang.trim() || 'zh',
      journal_title: form.journalTitle.trim(),
      journal_id: form.journalId.trim(),
      issn: form.issn.trim(),
      publisher_name: form.publisherName.trim(),
      subject: form.subject.trim(),
      pub_year: form.pubYear.trim(),
      pub_month: form.pubMonth.trim(),
      pub_day: form.pubDay.trim(),
      abstract: form.abstract.trim(),
      keywords: form.keywords.map((item) => item.trim()).filter(Boolean),
      authors: parseArray('作者', form.authorsJson),
      affiliations: parseArray('单位', form.affiliationsJson),
      sections: parseArray('章节', form.sectionsJson),
      figures: parseArray('图片', form.figuresJson),
      tables: parseArray('表格', form.tablesJson),
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

      <h3 class="group-title">出版元数据</h3>
      <div class="metadata-grid">
        <el-form-item label="DOI">
          <el-input v-model="form.doi" placeholder="10.xxxx/article-id" />
        </el-form-item>
        <el-form-item label="文章类型 article-type">
          <el-input v-model="form.articleType" placeholder="research-article" />
        </el-form-item>
        <el-form-item label="语言 xml:lang">
          <el-input v-model="form.lang" placeholder="zh" />
        </el-form-item>
        <el-form-item label="学科 subject">
          <el-input v-model="form.subject" placeholder="数字出版" />
        </el-form-item>
        <el-form-item label="期刊名称">
          <el-input v-model="form.journalTitle" />
        </el-form-item>
        <el-form-item label="期刊 ID">
          <el-input v-model="form.journalId" />
        </el-form-item>
        <el-form-item label="ISSN">
          <el-input v-model="form.issn" placeholder="1234-5678" />
        </el-form-item>
        <el-form-item label="出版者">
          <el-input v-model="form.publisherName" />
        </el-form-item>
        <el-form-item label="出版日期">
          <div class="date-grid">
            <el-input v-model="form.pubYear" placeholder="年 YYYY" />
            <el-input v-model="form.pubMonth" placeholder="月 MM" />
            <el-input v-model="form.pubDay" placeholder="日 DD" />
          </div>
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
        <el-form-item label="表格与表题 tables">
          <el-input v-model="form.tablesJson" type="textarea" :rows="14" />
        </el-form-item>
        <el-form-item label="数学公式 formulas">
          <el-input v-model="form.formulasJson" type="textarea" :rows="14" />
        </el-form-item>
        <el-form-item label="参考文献 references（支持 authors/article_title/source/year/doi 等细粒度字段）" class="wide">
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
.basic-grid, .metadata-grid, .json-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 22px; }
.group-title { margin: 24px 0 16px; padding-bottom: 8px; border-bottom: 1px solid #ded9cd; color: #253b36; font-family: Georgia, "Noto Serif SC", serif; font-size: 17px; }
.date-grid { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 8px; width: 100%; }
.json-grid { margin-top: 8px; }
.wide { grid-column: 1 / 3; }
.editor-actions { display: flex; align-items: center; justify-content: space-between; padding-top: 22px; border-top: 1px solid #ded9cd; }
.editor-actions span { color: #7c8883; font-size: 12px; }
.editor-actions .el-button { border-radius: 2px; font-weight: 700; }
:deep(.el-form-item__label) { color: #354943; font-weight: 700; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner), :deep(.el-select__wrapper) { border-radius: 2px; }
:deep(.el-textarea__inner) { font-family: "Cascadia Code", Consolas, monospace; line-height: 1.6; }
@media (max-width: 850px) {
  .basic-grid, .metadata-grid, .json-grid { grid-template-columns: 1fr; }
  .wide { grid-column: auto; }
  .editor-actions { align-items: stretch; flex-direction: column; gap: 14px; }
}
</style>
