<template>
  <div class="case-selector">
    <div class="selector-toolbar">
      <el-input v-model="searchText" placeholder="搜索用例..." size="small" clearable />
      <span class="selector-count">已选 {{ selectedCount }} 条</span>
    </div>
    <div class="selector-tree" v-loading="loading">
      <template v-if="tree.children && tree.children.length">
        <template v-for="node in tree.children" :key="node.name">
          <selector-node
            :node="node"
            :depth="0"
            :selected-ids="selectedIds"
            :search-text="searchText"
            @toggle-case="toggleCase"
          />
        </template>
      </template>
      <div v-else class="selector-empty">请先收集用例</div>
    </div>
    <div class="selector-footer">
      <el-button size="small" @click="selectAll">全选</el-button>
      <el-button size="small" @click="deselectAll">取消</el-button>
      <span class="footer-count">共 {{ totalCases }} 条，已选 {{ selectedCount }} 条</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SelectorNode from './SelectorNode.vue'

const props = defineProps({
  tree: { type: Object, default: () => ({ children: [] }) },
  flatCases: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const searchText = ref('')

const selectedIds = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const totalCases = computed(() => props.flatCases.length)
const selectedCount = computed(() => selectedIds.value.length)

const toggleCase = (nodeid) => {
  const i = selectedIds.value.indexOf(nodeid)
  if (i >= 0) {
    emit('update:modelValue', [...selectedIds.value.slice(0, i), ...selectedIds.value.slice(i + 1)])
  } else {
    emit('update:modelValue', [...selectedIds.value, nodeid])
  }
}

const selectAll = () => {
  emit('update:modelValue', props.flatCases.map(c => c.nodeid))
}

const deselectAll = () => {
  emit('update:modelValue', [])
}
</script>

<style scoped>
.case-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.selector-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}
.selector-toolbar .el-input {
  flex: 1;
}
.selector-count {
  font-size: 13px;
  color: #409eff;
  font-weight: 500;
}
.selector-tree {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 6px 4px;
  min-height: 180px;
  max-height: 400px;
  overflow-y: auto;
}
.selector-empty {
  text-align: center;
  padding: 60px 0;
  color: #909399;
}
.selector-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}
.footer-count {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}
</style>
