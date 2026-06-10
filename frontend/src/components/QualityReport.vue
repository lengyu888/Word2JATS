<script setup>
import { computed } from 'vue'

const props = defineProps({ validation: { type: Object, required: true } })
const cards = computed(() => [
  {
    title: 'XML 合法性',
    passed: props.validation.xml_well_formed,
    detail: props.validation.xml_well_formed ? 'XML 可被解析' : 'XML 解析失败',
  },
  {
    title: 'JATS Schema',
    passed: props.validation.jats_schema_valid,
    detail: props.validation.jats_schema_valid === null
      ? '未配置本地官方 Schema'
      : props.validation.schema_file || 'Schema 校验已执行',
  },
  {
    title: '业务完整性',
    passed: props.validation.business_rules?.passed ?? props.validation.passed,
    detail: `${props.validation.errors?.length || 0} 错误，${props.validation.warnings?.length || 0} 警告`,
  },
  {
    title: '引用完整性',
    passed: !(props.validation.warnings || []).some((item) => item.includes('引用目标') || item.includes('交叉引用')),
    detail: `${props.validation.xref_checks?.length || 0} 项引用检查记录`,
  },
])
</script>

<template>
  <div class="quality-report">
    <div v-for="card in cards" :key="card.title" :class="['quality-card', card.passed === true ? 'pass' : card.passed === false ? 'fail' : 'unknown']">
      <span>{{ card.title }}</span>
      <strong>{{ card.passed === true ? '通过' : card.passed === false ? '需处理' : '未配置' }}</strong>
      <p>{{ card.detail }}</p>
    </div>
  </div>
</template>

<style scoped>
.quality-report { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 10px 4px; }
.quality-card { min-height: 180px; padding: 24px; border: 1px solid #ded9cd; background: #fffef9; }
.quality-card::before { content: ""; display: block; width: 34px; height: 4px; margin-bottom: 30px; background: #8b918e; }
.quality-card.pass::before { background: #238263; }.quality-card.fail::before { background: #b44732; }.quality-card.unknown::before { background: #c58a18; }
.quality-card span { color: #64716c; font-size: 12px; font-weight: 700; }
.quality-card strong { display: block; margin: 12px 0; font: 28px Georgia, "Noto Serif SC", serif; }
.quality-card p { margin: 0; color: #89928e; font-size: 12px; line-height: 1.7; }
@media (max-width: 900px) { .quality-report { grid-template-columns: 1fr 1fr; } }
</style>
