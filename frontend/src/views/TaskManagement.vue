<template>
  <div class="task-mgmt">
    <div class="panel-header">
      <span>测试任务</span>
      <el-button size="small" type="primary" @click="showCreate = true">
        <el-icon><Plus /></el-icon>创建任务
      </el-button>
    </div>

    <el-table :data="tasks" stripe v-loading="loading" empty-text="暂无任务" size="small" style="flex:1">
      <el-table-column prop="id" label="ID" width="50" />
      <el-table-column prop="name" label="任务名称" min-width="140" show-overflow-tooltip />
      <el-table-column label="用例数" width="60">
        <template #default="{ row }">{{ row.nodeids?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="运行次数" width="70">
        <template #default="{ row }">{{ taskRunMap[row.id]?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="runsOf(row.id).length > 0 && runsOf(row.id)[0].status === 'running'" type="warning" size="small">运行中</el-tag>
          <el-tag v-else-if="runsOf(row.id).length > 0" type="success" size="small">已完成</el-tag>
          <el-tag v-else type="info" size="small">未运行</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="executeTask(row)" :loading="executingId === row.id">
            <el-icon><CaretRight /></el-icon>执行
          </el-button>
          <el-button size="small" plain @click="viewTaskReport(row)">报告</el-button>
          <el-button size="small" type="primary" link @click="editTask(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteTask(row.id)">
            <template #reference>
              <el-button size="small" type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        small
        @current-change="loadTasks"
      />
    </div>

    <el-dialog :model-value="showCreate || showEdit" title="任务" width="620px" :close-on-click-modal="false" @close="closeDialog">
      <el-form :model="form" label-width="70px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="任务名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
        <el-form-item label="用例">
          <case-selector
            :tree="caseTree"
            :flat-cases="flatCases"
            :loading="casesLoading"
            :model-value="form.nodeids"
            @update:model-value="form.nodeids = $event"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="saveTask" :loading="saving">{{ showEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import CaseSelector from '../components/CaseSelector.vue'

const props = defineProps({
  projectId: { type: Number, required: true },
  flatCases: { type: Array, default: () => [] },
  caseTree: { type: Object, default: () => ({ children: [] }) },
  casesLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['viewTaskReport'])

const loading = ref(false)
const tasks = ref([])
const taskRuns = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(8)
const showCreate = ref(false)
const showEdit = ref(false)
const editingTask = ref(null)
const saving = ref(false)
const executingId = ref(0)

const form = reactive({
  name: '',
  description: '',
  nodeids: [],
})

const taskRunMap = computed(() => {
  const map = {}
  for (const run of taskRuns.value) {
    if (!map[run.task_id]) map[run.task_id] = []
    map[run.task_id].push(run)
  }
  return map
})

const runsOf = (taskId) => {
  return taskRunMap.value[taskId] || []
}

const loadTasks = async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/projects/${props.projectId}/tasks`, {
      params: { page: page.value, page_size: pageSize.value },
    })
    tasks.value = data.items || []
    total.value = data.total || 0
    const { data: runs } = await api.get(`/projects/${props.projectId}/tasks/runs/all`)
    taskRuns.value = runs.items || []
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

const closeDialog = () => {
  showCreate.value = false
  showEdit.value = false
  editingTask.value = null
  form.name = ''
  form.description = ''
  form.nodeids = []
}

const saveTask = async () => {
  if (!form.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (form.nodeids.length === 0) {
    ElMessage.warning('请至少选择一条用例')
    return
  }
  saving.value = true
  try {
    if (showEdit.value && editingTask.value) {
      await api.put(`/projects/${props.projectId}/tasks/${editingTask.value.id}`, {
        name: form.name,
        description: form.description,
        nodeids: form.nodeids,
      })
      ElMessage.success('任务已更新')
    } else {
      await api.post(`/projects/${props.projectId}/tasks`, {
        name: form.name,
        description: form.description,
        nodeids: form.nodeids,
      })
      ElMessage.success('任务创建成功')
    }
    closeDialog()
    page.value = 1
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

const editTask = (task) => {
  editingTask.value = task
  form.name = task.name
  form.description = task.description
  form.nodeids = task.nodeids || []
  showEdit.value = true
}

const deleteTask = async (taskId) => {
  try {
    await api.delete(`/projects/${props.projectId}/tasks/${taskId}`)
    ElMessage.success('任务已删除')
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const executeTask = async (task) => {
  executingId.value = task.id
  try {
    const { data } = await api.post(`/projects/${props.projectId}/tasks/${task.id}/run`)
    ElMessage.success(`任务已启动，${data.count} 条用例`)
    setTimeout(async () => {
      const { data: runs } = await api.get(`/projects/${props.projectId}/tasks/runs/all`)
      taskRuns.value = runs.items || []
    }, 2000)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    executingId.value = 0
  }
}

const viewTaskReport = (task) => {
  emit('viewTaskReport', task.name)
}

watch(() => props.projectId, () => {
  page.value = 1
  loadTasks()
})
onMounted(loadTasks)
</script>

<style scoped>
.task-mgmt {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  margin-top: 10px;
}
.never-run {
  color: #909399;
  font-size: 12px;
}
</style>
