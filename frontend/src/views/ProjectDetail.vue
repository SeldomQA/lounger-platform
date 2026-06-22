<template>
  <div class="project-detail">
    <div class="page-header">
      <el-button @click="$router.push('/projects')" text>
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <el-select
        v-if="projects.length"
        v-model="currentProjectId"
        class="project-switcher"
        size="large"
        @change="switchProject"
      >
        <el-option
          v-for="p in projects"
          :key="p.id"
          :label="p.name"
          :value="p.id"
        />
      </el-select>
      <el-tabs v-if="project" v-model="activeTab" class="page-tabs" @tab-click="onTabClick">
        <el-tab-pane label="用例管理" name="cases" />
        <el-tab-pane label="任务管理" name="tasks" />
        <el-tab-pane label="任务报告" name="reports" />
      </el-tabs>
    </div>

    <div v-if="!project" class="loading-state">
      <el-icon :size="40" class="is-loading"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- Tasks tab -->
    <div v-else-if="activeTab === 'tasks'" class="main-layout">
      <task-management
        :project-id="projectId"
        :flat-cases="flatCases"
        :case-tree="tree"
        :cases-loading="casesLoading"
        @view-task-report="handleViewTaskReport"
      />
    </div>

    <!-- Reports tab → task runs -->
    <div v-else-if="activeTab === 'reports'" class="main-layout">
      <div class="report-panel" v-loading="taskRunsLoading">
        <div class="panel-header">
          <span>任务报告</span>
        </div>
        <div class="filter-bar">
          <el-select v-model="runFilterTaskName" placeholder="任务名称" size="small" clearable filterable style="width:160px" @change="searchTaskRuns">
            <el-option v-for="opt in taskOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <div style="width:240px"><el-date-picker v-model="runFilterDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" size="small" value-format="YYYY-MM-DD" style="width:100%" /></div>
          <el-button size="small" type="primary" @click="searchTaskRuns">查询</el-button>
          <el-button size="small" @click="resetTaskRuns">重置</el-button>
        </div>
        <el-table :data="taskRunList" stripe empty-text="暂无任务报告" size="small" style="flex:1">
          <el-table-column label="任务名称" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ taskNameMap[row.task_id] || `任务 #${row.task_id}` }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'completed'" type="success" size="small">完成</el-tag>
              <el-tag v-else-if="row.status === 'error'" type="danger" size="small">失败</el-tag>
              <el-tag v-else-if="row.status === 'running'" type="warning" size="small">运行中</el-tag>
              <el-tag v-else size="small" type="info">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="总数" width="55">
            <template #default="{ row }">{{ row.total }}</template>
          </el-table-column>
          <el-table-column label="通过" width="55">
            <template #default="{ row }"><span class="stat-pass">{{ row.passed }}</span></template>
          </el-table-column>
          <el-table-column label="失败" width="55">
            <template #default="{ row }"><span :class="row.failure > 0 ? 'stat-fail' : ''">{{ row.failure }}</span></template>
          </el-table-column>
          <el-table-column label="错误" width="55">
            <template #default="{ row }"><span :class="row.error > 0 ? 'stat-fail' : ''">{{ row.error }}</span></template>
          </el-table-column>
          <el-table-column label="跳过" width="55">
            <template #default="{ row }">{{ row.skipped }}</template>
          </el-table-column>
          <el-table-column label="通过率" width="90">
            <template #default="{ row }">
              <el-progress :percentage="taskRunPassRate(row)" :color="passRateColor({ tests: row.total, passed: row.passed })" :stroke-width="8" :show-text="false" />
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="65">
            <template #default="{ row }">{{ row.run_time }}s</template>
          </el-table-column>
          <el-table-column label="运行时间" min-width="145">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.report_id" size="small" type="primary" link @click="showTaskRunDetail(row)">详情</el-button>
              <el-popconfirm v-if="row.report_id" title="确定删除此报告？" @confirm="deleteReport(row.report_id)">
                <template #reference>
                  <el-button size="small" type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
              <span v-else class="never-run">-</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar" v-if="taskRunTotal > 0">
          <el-pagination
            v-model:current-page="runPage"
            :page-size="runPageSize"
            :total="taskRunTotal"
            layout="total, prev, pager, next"
            small
            @current-change="loadTaskRuns"
          />
        </div>
      </div>
    </div>

    <!-- Cases tab (restored original left-right design) -->
    <div v-else class="main-layout">
      <div class="left-panel">
        <div class="panel-header">
          <span>用例列表 ({{ totalCases }})</span>
          <el-button size="small" type="primary" @click="collectCases" :loading="collecting">
            收集用例
          </el-button>
        </div>
        <div class="tree-toolbar">
          <el-input v-model="searchText" placeholder="搜索用例..." size="small" clearable />
          <el-button size="small" @click="selectAll">全选</el-button>
          <el-button size="small" @click="deselectAll">取消</el-button>
        </div>
        <div class="tree-scroll" v-loading="casesLoading">
          <div v-if="flatCases.length === 0" class="empty-hint">请先「收集用例」</div>
          <template v-else>
            <tree-node
              v-for="node in tree.children"
              :key="node.name"
              :node="node"
              :depth="0"
              :selected-ids="selectedIds"
              :search-text="searchText"
              @toggle-case="toggleCase"
              @run-node="runNodeids"
            />
          </template>
        </div>
        <div class="run-actions">
          <el-button type="success" @click="runSelected" :disabled="selectedCount === 0">
            <el-icon><VideoPlay /></el-icon>执行选中 ({{ selectedCount }})
          </el-button>
          <el-button type="primary" @click="runAll" :disabled="flatCases.length === 0">
            <el-icon><VideoPlay /></el-icon>执行全部
          </el-button>
        </div>
      </div>

      <div class="right-panel">
        <div class="panel-header">
          <span>
            运行输出
            <el-tag v-if="runStatus" :type="statusTagType" size="small" class="status-tag">{{ statusText }}</el-tag>
          </span>
          <el-button size="small" @click="clearLogs" :disabled="!logLines.length">清空</el-button>
        </div>
        <div class="log-scroll" ref="logContainer">
          <div v-for="(line, i) in logLines" :key="i" class="log-line" :class="lineClass(line)">{{ line }}</div>
          <div v-if="logLines.length === 0" class="log-empty">选择用例，点击「执行」开始</div>
        </div>
      </div>
    </div>

    <report-detail-dialog v-model:visible="reportDetailVisible" :report="reportDetailData" />

    <el-dialog v-model="caseDetailVisible" :title="caseDetail.name" width="700px">
      <div v-if="caseDetail.failure_out" class="case-err">
        <h4>失败信息</h4>
        <pre>{{ caseDetail.failure_out }}</pre>
      </div>
      <div v-if="caseDetail.error_out" class="case-err">
        <h4>错误信息</h4>
        <pre>{{ caseDetail.error_out }}</pre>
      </div>
      <div v-if="caseDetail.skipped_message" class="case-err">
        <h4>跳过原因</h4>
        <pre>{{ caseDetail.skipped_message }}</pre>
      </div>
      <div v-if="caseDetail.system_out" class="case-out">
        <h4>标准输出</h4>
        <pre>{{ caseDetail.system_out }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import TreeNode from '../components/TreeNode.vue'
import TaskManagement from './TaskManagement.vue'
import ReportDetailDialog from '../components/ReportDetailDialog.vue'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))
const project = ref(null)
const projects = ref([])
const currentProjectId = ref(0)
const activeTab = ref('cases')
const tree = reactive({ children: [] })
const flatCases = ref([])
const selectedIds = ref([])
const searchText = ref('')
const casesLoading = ref(false)
const collecting = ref(false)

const logLines = reactive([])
const runStatus = ref('')
const eventSource = ref(null)
const logContainer = ref(null)

const taskRunList = ref([])
const taskRunTotal = ref(0)
const taskRunsLoading = ref(false)
const taskNameMap = ref({})
const taskOptions = ref([])
const runPage = ref(1)
const runPageSize = ref(10)
const runFilterTaskName = ref('')
const runFilterDateRange = ref(null)
const reportDetailVisible = ref(false)
const reportDetailCases = ref([])
const reportDetailData = ref(null)
const caseDetailVisible = ref(false)
const caseDetail = ref({})

const totalCases = computed(() => flatCases.value.length)
const selectedCount = computed(() => selectedIds.value.length)
const statusTagType = computed(() => {
  if (runStatus.value === 'running') return 'warning'
  if (runStatus.value === 'completed') return 'success'
  return 'danger'
})
const statusText = computed(() => {
  if (runStatus.value === 'running') return '运行中'
  if (runStatus.value === 'completed') return '已完成'
  if (runStatus.value === 'error') return '错误'
  return ''
})

const passRate = (r) => r.tests === 0 ? 0 : Math.round((r.passed / r.tests) * 100)
const taskRunPassRate = (r) => r.total === 0 ? 0 : Math.round((r.passed / r.total) * 100)
const passRateColor = (r) => {
  const rate = passRate(r)
  if (rate >= 90) return '#67c23a'
  if (rate >= 70) return '#e6a23c'
  return '#f56c6c'
}
const resultType = (r) => {
  if (r === 'passed') return 'success'
  if (r === 'failed') return 'danger'
  if (r === 'error') return 'danger'
  return 'warning'
}
const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const loadProject = async () => {
  const { data } = await api.get('/projects')
  projects.value = data
  project.value = data.find(p => p.id === projectId.value)
  currentProjectId.value = projectId.value
}

const switchProject = (id) => {
  router.push(`/projects/${id}`)
}

const onTabClick = (tab) => {
  if (tab.props.name === 'reports') {
    loadTaskRuns()
  }
}

const collectCases = async () => {
  collecting.value = true
  casesLoading.value = true
  try {
    const { data } = await api.post(`/projects/${projectId.value}/cases/collect`)
    ElMessage.success(`收集到 ${data.count} 条用例`)
    await loadCases()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    collecting.value = false
    casesLoading.value = false
  }
}

const loadCases = async () => {
  casesLoading.value = true
  try {
    const { data } = await api.get(`/projects/${projectId.value}/cases/tree`)
    Object.assign(tree, data.tree || { children: [] })
    flatCases.value = data.flat || []
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    casesLoading.value = false
  }
}

const loadTaskRuns = async () => {
  taskRunsLoading.value = true
  try {
    const params = {
      page: runPage.value,
      page_size: runPageSize.value,
    }
    if (runFilterTaskName.value) params.task_name = runFilterTaskName.value
    if (runFilterDateRange.value && runFilterDateRange.value.length === 2) {
      params.date_from = runFilterDateRange.value[0]
      params.date_to = runFilterDateRange.value[1]
    }
    const { data } = await api.get(`/projects/${projectId.value}/tasks/runs/all`, { params })
    taskRunList.value = data.items || []
    taskRunTotal.value = data.total || 0

    const { data: tasksData } = await api.get(`/projects/${projectId.value}/tasks`, {
      params: { page: 1, page_size: 100 },
    })
    const map = {}
    const opts = []
    for (const t of tasksData.items || []) {
      map[t.id] = t.name
      opts.push({ label: t.name, value: t.name })
    }
    taskNameMap.value = map
    taskOptions.value = opts
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    taskRunsLoading.value = false
  }
}

const searchTaskRuns = () => {
  runPage.value = 1
  loadTaskRuns()
}

const resetTaskRuns = () => {
  runFilterTaskName.value = ''
  runFilterDateRange.value = null
  runPage.value = 1
  loadTaskRuns()
}

const showTaskRunDetail = async (run) => {
  if (!run.report_id) return
  try {
    const { data } = await api.get(`/projects/${projectId.value}/reports/${run.report_id}`)
    reportDetailData.value = data
    reportDetailCases.value = data.details || []
    reportDetailVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const showCaseDetail = (item) => {
  caseDetail.value = item
  caseDetailVisible.value = true
}

const deleteReport = async (reportId) => {
  try {
    await api.delete(`/projects/${projectId.value}/reports/${reportId}`)
    ElMessage.success('报告已删除')
    await loadTaskRuns()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const toggleCase = (nodeid) => {
  const i = selectedIds.value.indexOf(nodeid)
  if (i >= 0) {
    selectedIds.value = [...selectedIds.value.slice(0, i), ...selectedIds.value.slice(i + 1)]
  } else {
    selectedIds.value = [...selectedIds.value, nodeid]
  }
}

const selectAll = () => { selectedIds.value = flatCases.value.map(c => c.nodeid) }
const deselectAll = () => { selectedIds.value = [] }

const runNodeids = (ids) => startRun(ids.map(String))

const runSelected = () => {
  if (selectedCount.value === 0) return
  startRun([...selectedIds.value])
}

const runAll = () => {
  const ids = flatCases.value.map(c => c.nodeid)
  if (ids.length === 0) return
  startRun(ids)
}

const startRun = async (nodeids) => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  try {
    const { data } = await api.post(`/projects/${projectId.value}/cases/run`, { nodeids })
    runStatus.value = 'running'
    logLines.length = 0
    connectSSE(data.run_id)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const handleViewTaskReport = (taskName) => {
  runFilterTaskName.value = taskName
  runPage.value = 1
  activeTab.value = 'reports'
  loadTaskRuns()
}

const connectSSE = (runId) => {
  eventSource.value = new EventSource(`/api/stream/${runId}`)
  eventSource.value.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.heartbeat) return
      if (msg.line) {
        logLines.push(msg.line)
        nextTick(() => scrollLog())
      }
      if (msg.done) {
        eventSource.value.close()
        eventSource.value = null
        runStatus.value = msg.exit_code === 0 ? 'completed' : 'error'
        loadTaskRuns()
      }
    } catch {}
  }
  eventSource.value.onerror = () => {
    if (eventSource.value?.readyState === EventSource.CLOSED) {
      eventSource.value = null
    }
  }
}

const scrollLog = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

const clearLogs = () => {
  logLines.length = 0
  runStatus.value = ''
}

const lineClass = (line) => {
  if (line.includes('PASSED')) return 'pass'
  if (line.includes('FAILED') || line.includes('ERROR')) return 'fail'
  if (line.includes('WARNING') || line.includes('skipped')) return 'warn'
  if (line.startsWith('──')) return 'summary'
  return ''
}

onBeforeUnmount(() => {
  if (eventSource.value) eventSource.value.close()
})

onMounted(async () => {
  await loadProject()
  await loadCases()
})

watch(() => route.params.id, async () => {
  runPage.value = 1
  runFilterTaskName.value = ''
  runFilterDateRange.value = null
  taskRunList.value = []
  taskRunTotal.value = 0
  await loadProject()
  await loadCases()
  if (activeTab.value === 'reports') {
    loadTaskRuns()
  }
})
</script>

<style scoped>
.project-detail {
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
  margin-bottom: 12px;
}
.page-header h2 {
  font-size: 18px;
  color: #303133;
  flex-shrink: 0;
}
.page-tabs {
  flex: 1;
}
.project-switcher {
  width: 200px;
  margin-left: 8px;
}
.loading-state {
  text-align: center;
  padding: 80px 0;
  color: #909399;
}

.main-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.left-panel,
.right-panel,
.report-panel {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  padding: 16px;
  min-height: 0;
}

.left-panel {
  flex: 0 0 35%;
  min-width: 0;
}

.right-panel {
  flex: 1;
  min-width: 0;
}

.report-panel {
  flex: 1;
}
.report-panel .el-table {
  flex: 1;
}
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  margin-top: 10px;
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

.tree-toolbar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-bottom: 8px;
}
.tree-toolbar .el-input {
  width: 150px;
}

.tree-scroll {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 6px 4px;
  min-height: 0;
}

.log-scroll {
  flex: 1;
  overflow-y: auto;
  background: #1a1a2e;
  color: #e0e0e0;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 0;
}

.log-line.pass { color: #67c23a; }
.log-line.fail { color: #f56c6c; }
.log-line.warn { color: #e6a23c; }
.log-line.summary { color: #409eff; font-weight: bold; }
.log-empty {
  text-align: center;
  padding: 60px 0;
  color: #666;
}

.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: #909399;
}

.run-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  margin-top: 10px;
}

.status-tag {
  margin-left: 6px;
}

.stat-pass { color: #67c23a; font-weight: 600; }
.stat-fail { color: #f56c6c; font-weight: 600; }
.case-err, .case-out { margin-bottom: 12px; }
.case-err h4 { color: #f56c6c; }
.case-err pre {
  background: #fff5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 300px;
}
.case-out pre {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 200px;
}
</style>
