<template>
  <div v-if="visible" class="tree-node-wrapper">
    <div v-if="isDir || isFile" class="tree-row" :class="{ 'tree-dir': isDir, 'tree-file': isFile }" :style="rowStyle" @click="toggleExpand">
      <span class="tree-arrow" :class="{ expanded }">
        <CaretRight />
      </span>
      <span class="tree-icon">{{ isDir ? '📁' : '📄' }}</span>
      <span class="tree-label">{{ node.name }}{{ isDir ? ` (${node.total_cases || 0})` : ` (${node.case_count || 0})` }}</span>
      <el-button v-if="isFile && node.cases?.length" size="small" circle type="success" class="run-btn" title="运行此文件所有用例" @click.stop="emitRun">
        <el-icon><CaretRight /></el-icon>
      </el-button>
    </div>

    <div v-if="isCase" class="tree-row tree-case" :class="{ selected: selectedIds.includes(node.nodeid) }" :style="rowStyle" @click="emitToggle">
      <input type="checkbox" class="tree-check" :checked="selectedIds.includes(node.nodeid)" @click="emitToggle" />
      <span class="tree-icon">🧪</span>
      <span class="tree-label" :title="node.description || node.name">{{ node.name }}</span>
      <el-button v-if="node.nodeid" size="small" circle type="success" class="run-btn" title="运行此用例" @click.stop="emitRun">
        <el-icon><CaretRight /></el-icon>
      </el-button>
    </div>

    <div v-if="(isDir || isFile) && expanded && children" class="tree-children">
      <tree-node
        v-for="child in children"
        :key="child.name + (child.nodeid || '')"
        :node="child"
        :depth="depth + 1"
        :selected-ids="selectedIds"
        :search-text="searchText"
        @toggle-case="(id) => $emit('toggleCase', id)"
        @run-node="(ids) => $emit('runNode', ids)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { CaretRight } from '@element-plus/icons-vue'

const props = defineProps({
  node: Object,
  depth: { type: Number, default: 0 },
  selectedIds: { type: Array, default: () => [] },
  searchText: { type: String, default: '' },
})
const emit = defineEmits(['toggleCase', 'runNode'])

const isDir = props.node.type === 'dir'
const isFile = props.node.type === 'file'
const isCase = !isDir && !isFile

const expanded = ref(true)

const rowStyle = { paddingLeft: `${props.depth * 20 + 10}px` }

const children = computed(() => {
  if (isDir) return props.node.children
  if (isFile) return props.node.cases
  return null
})

const visible = computed(() => {
  if (!props.searchText) return true
  const q = props.searchText.toLowerCase()
  if (isCase) {
    return (props.node.name || '').toLowerCase().includes(q)
  }
  const kids = children.value
  if (!kids) return (props.node.name || '').toLowerCase().includes(q)
  return kids.some(k => {
    const kname = (k.name || '').toLowerCase()
    if (k.children) return k.children.some(c => (c.name || '').toLowerCase().includes(q))
    if (k.cases) return k.cases.some(c => (c.name || '').toLowerCase().includes(q))
    return kname.includes(q)
  }) || (props.node.name || '').toLowerCase().includes(q)
})

const toggleExpand = () => {
  expanded.value = !expanded.value
}

const emitToggle = () => {
  if (isCase) emit('toggleCase', props.node.nodeid)
}

const emitRun = () => {
  if (isCase) {
    emit('runNode', [props.node.nodeid])
  } else if (isFile && props.node.cases) {
    emit('runNode', props.node.cases.map(c => c.nodeid))
  }
}
</script>

<style scoped>
.tree-row {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 4px;
  user-select: none;
  min-height: 30px;
  transition: background 0.15s;
  position: relative;
}
.tree-row:hover {
  background: #f0f2f5;
}
.tree-dir {
  font-weight: 500;
  color: #409eff;
}
.tree-file {
  color: #303133;
}
.tree-case {
  color: #606266;
  padding-left: 30px;
}
.tree-case.selected {
  background: #ecf5ff;
}
.tree-check {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #409eff;
  margin-right: 4px;
  flex-shrink: 0;
}
.tree-arrow {
  width: 14px;
  font-size: 12px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s;
}
.tree-arrow.expanded {
  transform: rotate(90deg);
}
.tree-icon {
  width: 18px;
  text-align: center;
  flex-shrink: 0;
  font-size: 13px;
}
.tree-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.run-btn {
  opacity: 0;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  --el-button-size: 24px;
  transition: opacity 0.15s;
  margin-left: 4px;
}
.tree-row:hover .run-btn {
  opacity: 1;
}
.tree-children {
  overflow: hidden;
}
</style>
