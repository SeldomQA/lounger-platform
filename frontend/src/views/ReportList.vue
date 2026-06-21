<template>
  <div class="report-list">
    <div class="page-header">
      <el-button @click="$router.push(`/projects/${projectId}`)" text>
        <el-icon><ArrowLeft /></el-icon>返回用例管理
      </el-button>
      <h2>测试报告</h2>
    </div>

    <el-table :data="reports" stripe v-loading="loading" empty-text="暂无报告">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="报告名称" min-width="200" show-overflow-tooltip />
      <el-table-column label="总数" width="70">
        <template #default="{ row }">{{ row.tests }}</template>
      </el-table-column>
      <el-table-column label="通过" width="70">
        <template #default="{ row }">
          <span class="stat-pass">{{ row.passed }}</span>
        </template>
      </el-table-column>
      <el-table-column label="失败" width="70">
        <template #default="{ row }">
          <span :class="row.failure > 0 ? 'stat-fail' : ''">{{ row.failure }}</span>
        </template>
      </el-table-column>
      <el-table-column label="错误" width="70">
        <template #default="{ row }">
          <span :class="row.error > 0 ? 'stat-fail' : ''">{{ row.error }}</span>
        </template>
      </el-table-column>
      <el-table-column label="跳过" width="70">
        <template #default="{ row }">{{ row.skipped }}</template>
      </el-table-column>
      <el-table-column label="通过率" width="80">
        <template #default="{ row }">
          <el-progress
            :percentage="passRate(row)"
            :color="passRateColor(row)"
            :stroke-width="8"
            :show-text="false"
          />
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">{{ row.run_time }}s</template>
      </el-table-column>
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="showDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="detailVisible" title="报告详情" width="900px" top="5vh">
      <el-table :data="detailCases" stripe max-height="500">
        <el-table-column prop="class_name" label="类名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="name" label="用例名" min-width="200" show-overflow-tooltip />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="run_time" label="耗时" width="70" />
        <el-table-column label="详情" width="80">
          <template #default="{ row }">
            <el-button v-if="row.result !== 'passed'" size="small" link type="primary" @click="showCaseDetail(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))
const reports = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const detailCases = ref([])
const caseDetailVisible = ref(false)
const caseDetail = ref({})

const passRate = (r) => r.tests === 0 ? 0 : Math.round((r.passed / r.tests) * 100)
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

const loadReports = async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/projects/${projectId.value}/reports`)
    reports.value = data
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

const showDetail = (report) => {
  detailCases.value = report.details || []
  detailVisible.value = true
}

const showCaseDetail = (item) => {
  caseDetail.value = item
  caseDetailVisible.value = true
}

onMounted(async () => {
  await loadReports()
  const reportId = route.query.report_id
  if (reportId) {
    const found = reports.value.find(r => r.id === Number(reportId))
    if (found) {
      showDetail(found)
    }
  }
})
</script>

<style scoped>
.report-list {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.page-header h2 {
  font-size: 18px;
  color: #303133;
}
.stat-pass { color: #67c23a; font-weight: 600; }
.stat-fail { color: #f56c6c; font-weight: 600; }
.case-err, .case-out {
  margin-bottom: 12px;
}
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
