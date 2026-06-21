<template>
  <div v-if="visible" class="sn-wrapper">
    <div v-if="isDir || isFile" class="sn-row" :style="rowStyle" @click="toggleExpand">
      <span class="sn-arrow" :class="{ expanded }">
        <CaretRight />
      </span>
      <span class="sn-icon">{{ isDir ? '📁' : '📄' }}</span>
      <span class="sn-label">{{ node.name }}{{ isDir ? ` (${node.total_cases || 0})` : ` (${node.case_count || 0})` }}</span>
    </div>

    <div v-if="isCase" class="sn-row sn-case" :class="{ selected: selectedIds.includes(node.nodeid) }" :style="rowStyle" @click="emitToggle">
      <input type="checkbox" class="sn-check" :checked="selectedIds.includes(node.nodeid)" @click.stop />
      <span class="sn-icon">🧪</span>
      <span class="sn-label" :title="node.description || node.name">{{ node.name }}</span>
    </div>

    <div v-if="(isDir || isFile) && expanded && children" class="sn-children">
      <selector-node
        v-for="child in children"
        :key="child.name + (child.nodeid || '')"
        :node="child"
        :depth="depth + 1"
        :selected-ids="selectedIds"
        :search-text="searchText"
        @toggle-case="(id) => $emit('toggleCase', id)"
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
const emit = defineEmits(['toggleCase'])

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

const toggleExpand = () => { expanded.value = !expanded.value }

const emitToggle = () => {
  if (isCase) emit('toggleCase', props.node.nodeid)
}
</script>

<style scoped>
.sn-row {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 3px;
  user-select: none;
  min-height: 28px;
  transition: background 0.1s;
}
.sn-row:hover {
  background: #f0f2f5;
}
.sn-case.selected {
  background: #ecf5ff;
}
.sn-check {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: #409eff;
  margin-right: 4px;
  flex-shrink: 0;
}
.sn-arrow {
  width: 14px;
  font-size: 12px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s;
}
.sn-arrow.expanded {
  transform: rotate(90deg);
}
.sn-icon {
  width: 16px;
  text-align: center;
  flex-shrink: 0;
  font-size: 12px;
}
.sn-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.sn-children {
  overflow: hidden;
}
</style>
