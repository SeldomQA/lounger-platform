<template>
  <el-dialog v-model="dialogVisible" title="报告详情" width="1000px" top="5vh" @closed="handleClose">
    <div v-if="!report" class="loading-state">加载中...</div>
    <template v-else>
      <div class="report-summary">
        <div class="stat-cards">
          <div class="stat-card total">
            <span class="stat-num">{{ report.tests }}</span>
            <span class="stat-label">总计</span>
          </div>
          <div class="stat-card passed">
            <span class="stat-num">{{ report.passed }}</span>
            <span class="stat-label">通过</span>
          </div>
          <div class="stat-card failed">
            <span class="stat-num">{{ report.failure }}</span>
            <span class="stat-label">失败</span>
          </div>
          <div class="stat-card error">
            <span class="stat-num">{{ report.error }}</span>
            <span class="stat-label">错误</span>
          </div>
          <div class="stat-card skipped">
            <span class="stat-num">{{ report.skipped }}</span>
            <span class="stat-label">跳过</span>
          </div>
        </div>
        <div class="chart-card">
          <div class="chart-title">结果分布</div>
          <v-chart :option="chartOption" autoresize style="height:200px;width:100%" />
        </div>
      </div>

      <el-table
        :data="report.details"
        stripe
        max-height="480"
        row-key="id"
      >
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div class="expand-log">
              <div v-if="row.run_log" class="log-section">
                <pre class="log-content">{{ row.run_log }}</pre>
              </div>
              <div v-if="row.failure_out" class="err-section">
                <div class="err-label">失败信息</div>
                <pre class="err-content">{{ row.failure_out }}</pre>
              </div>
              <div v-if="row.error_out" class="err-section">
                <div class="err-label">错误信息</div>
                <pre class="err-content">{{ row.error_out }}</pre>
              </div>
              <div v-if="row.skipped_message" class="err-section">
                <div class="err-label">跳过原因</div>
                <pre class="err-content">{{ row.skipped_message }}</pre>
              </div>
              <div v-if="!row.run_log && !row.failure_out && !row.error_out && !row.skipped_message" class="log-empty">暂无信息</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="类名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="name" label="用例名" min-width="200" show-overflow-tooltip />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="resultType(row.result)" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="run_time" label="耗时" width="70" />
      </el-table>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  visible: { type: Boolean, default: false },
  report: { type: Object, default: null },
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const resultType = (r) => {
  if (r === 'passed') return 'success'
  if (r === 'failed') return 'danger'
  if (r === 'error') return 'danger'
  return 'warning'
}

const chartOption = computed(() => {
  if (!props.report) return {}
  return {
    title: { show: false },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      bottom: 0,
      left: 'center',
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '48%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{d}%',
          fontSize: 12,
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: (() => {
          const data = []
          if (props.report.passed > 0) data.push({ value: props.report.passed, name: '通过', itemStyle: { color: '#67c23a' } })
          if (props.report.failure > 0) data.push({ value: props.report.failure, name: '失败', itemStyle: { color: '#f56c6c' } })
          if (props.report.error > 0) data.push({ value: props.report.error, name: '错误', itemStyle: { color: '#e6a23c' } })
          if (props.report.skipped > 0) data.push({ value: props.report.skipped, name: '跳过', itemStyle: { color: '#909399' } })
          return data
        })(),
      },
    ],
  }
})

const handleClose = () => {}
</script>

<style scoped>
.report-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  align-items: flex-start;
}
.stat-cards {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 70px;
  height: 70px;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
}
.stat-card.total { background: #409eff }
.stat-card.passed { background: #67c23a }
.stat-card.failed { background: #f56c6c }
.stat-card.error { background: #e6a23c }
.stat-card.skipped { background: #909399 }
.stat-num { font-size: 22px; line-height: 1.2 }
.stat-label { font-size: 11px; opacity: 0.9 }
.chart-card {
  flex: 1;
  min-width: 280px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  padding: 12px 8px 4px;
}
.chart-title {
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}
.expand-log {
  padding: 8px 16px 8px 48px;
  background: #fafafa;
}
.log-section {
  margin-bottom: 6px;
}
.log-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  color: #333;
}
.err-section {
  margin-bottom: 6px;
}
.err-label {
  font-size: 13px;
  font-weight: 600;
  color: #f56c6c;
  margin-bottom: 4px;
}
.err-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  background: #fef0f0;
  padding: 8px 10px;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}
.log-empty {
  color: #999;
  font-size: 13px;
}
.loading-state {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
