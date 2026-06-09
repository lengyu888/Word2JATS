<script setup>
defineProps({ data: { type: Object, required: true } })
</script>

<template>
  <pre class="code-view">{{ JSON.stringify(data, null, 2) }}</pre>
</template>

<style scoped>
.code-view { margin: 0; min-height: 480px; padding: 24px; overflow: auto; background: #12201e; color: #cfe6df; font: 13px/1.75 "Cascadia Code", Consolas, monospace; tab-size: 2; }
</style>
