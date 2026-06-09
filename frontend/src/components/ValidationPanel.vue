<script setup>
import { computed } from 'vue'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({ validation: { type: Object, required: true } })
const requiredCheckCount = 7
const passedCount = computed(() => Math.max(0, requiredCheckCount - props.validation.errors.length))
</script>

<template>
  <div class="validation">
    <div class="summary-grid">
      <div :class="['status-card', validation.passed ? 'passed' : 'failed']">
        <el-icon><CircleCheckFilled v-if="validation.passed" /><WarningFilled v-else /></el-icon>
        <div>
          <span>VALIDATION STATUS</span>
          <strong>{{ validation.passed ? 'JATS 基础校验通过' : '存在阻断性错误' }}</strong>
        </div>
      </div>

      <div class="metric-card success">
        <span>通过项</span>
        <b>{{ passedCount }}</b>
        <small>共 {{ requiredCheckCount }} 项阻断性检查</small>
      </div>
      <div class="metric-card error">
        <span>错误项</span>
        <b>{{ validation.errors.length }}</b>
        <small>需要修正后再交付</small>
      </div>
      <div class="metric-card warning">
        <span>警告项</span>
        <b>{{ validation.warnings.length }}</b>
        <small>建议人工复核</small>
      </div>
    </div>

    <el-alert
      v-if="validation.passed"
      title="所有阻断性检查均已通过，生成的 XML 具备基础 JATS 交付条件。"
      type="success"
      show-icon
      :closable="false"
      class="success-alert"
    />

    <div class="message-grid">
      <div class="message-column errors">
        <h3>错误 <b>{{ validation.errors.length }}</b></h3>
        <el-alert v-for="error in validation.errors" :key="error" :title="error" type="error" show-icon :closable="false" />
        <p v-if="!validation.errors.length">未发现阻断性错误。</p>
      </div>
      <div class="message-column warnings">
        <h3>警告 <b>{{ validation.warnings.length }}</b></h3>
        <el-alert v-for="warning in validation.warnings" :key="warning" :title="warning" type="warning" show-icon :closable="false" />
        <p v-if="!validation.warnings.length">未发现需要人工复核的警告。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.validation { padding: 6px; }
.summary-grid { display: grid; grid-template-columns: 1.7fr repeat(3, 1fr); gap: 14px; }
.status-card { display: flex; align-items: center; gap: 16px; min-height: 140px; padding: 24px; color: white; }
.status-card.passed { background: #006d77; }
.status-card.failed { background: #b44732; }
.status-card .el-icon { font-size: 44px; }
.status-card span { display: block; margin-bottom: 8px; opacity: .75; font-size: 10px; letter-spacing: .14em; }
.status-card strong { font-family: Georgia, "Noto Serif SC", serif; font-size: 22px; }
.metric-card { display: flex; flex-direction: column; justify-content: center; min-height: 140px; padding: 20px; border: 1px solid #ded9cd; background: #fffef9; }
.metric-card span { color: #68746f; font-size: 12px; font-weight: 700; }
.metric-card b { margin: 7px 0; font: 38px Georgia, serif; }
.metric-card small { color: #929a96; font-size: 10px; }
.metric-card.success b { color: #238263; }
.metric-card.error b { color: #b44732; }
.metric-card.warning b { color: #c58a18; }
.success-alert { margin-top: 18px; }
.message-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 14px; }
.message-column { padding: 18px; border: 1px solid #e0dccf; background: #fffef9; }
.message-column.errors { border-top: 3px solid #c45656; }
.message-column.warnings { border-top: 3px solid #d8a126; }
h3 { margin: 0 0 14px; color: #283a36; font-size: 15px; }
h3 b { margin-left: 6px; color: #006d77; }
.el-alert + .el-alert { margin-top: 8px; }
p { color: #85908c; font-size: 13px; }
@media (max-width: 1000px) {
  .summary-grid { grid-template-columns: 1fr 1fr; }
  .status-card { grid-column: 1 / 3; }
}
@media (max-width: 700px) {
  .summary-grid, .message-grid { grid-template-columns: 1fr; }
  .status-card { grid-column: auto; }
}
</style>
