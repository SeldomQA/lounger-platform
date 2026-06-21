<template>
  <div class="project-list">
    <div class="page-header">
      <h2>项目管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>创建项目
      </el-button>
    </div>

    <div v-loading="loading" class="card-grid">
      <div v-for="p in projects" :key="p.id" class="project-card" @click="goDetail(p.id)">
        <div class="card-top">
          <div class="card-title">
            <span class="project-icon">📁</span>
            <span class="project-name">{{ p.name }}</span>
          </div>
          <el-tag :type="statusType(p.status)" size="small">{{ statusText(p.status) }}</el-tag>
        </div>
        <div class="card-meta">
          <div class="meta-item">
            <span class="meta-label">Git</span>
            <span class="meta-value" :title="p.git_url || '未配置'">{{ p.git_url || '未配置' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">创建</span>
            <span class="meta-value">{{ formatTime(p.created_at) }}</span>
          </div>
        </div>
        <div class="card-actions" @click.stop>
          <el-button size="small" type="primary" @click="goDetail(p.id)">
            <el-icon><CaretRight /></el-icon>用例管理
          </el-button>
          <el-button v-if="p.git_url" size="small" type="warning" @click="refreshProject(p.id)" :loading="refreshingId === p.id">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
          <el-popconfirm title="确定删除此项目？" @confirm="deleteProject(p.id)">
            <template #reference>
              <el-button size="small" type="danger">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
      <div v-if="!loading && projects.length === 0" class="empty-state">
        <el-icon :size="48" color="#c0c4cc"><Folder /></el-icon>
        <p>暂无项目，点击右上角「创建项目」开始</p>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" title="创建项目" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="输入项目名称" />
        </el-form-item>
        <el-form-item label="Git 地址" required>
          <el-input v-model="form.git_url" placeholder="https://github.com/..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createProject" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const projects = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const refreshingId = ref(null)

const form = ref({ name: '', git_url: '' })

const statusType = (s) => ({ 0: 'info', 1: 'success', 2: 'warning' }[s] || 'info')
const statusText = (s) => ({ 0: '待克隆', 1: '就绪', 2: '执行中' }[s] || '未知')
const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''

const loadProjects = async () => {
  loading.value = true
  try {
    const { data } = await api.get('/projects')
    projects.value = data
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

const createProject = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!form.value.git_url.trim()) {
    ElMessage.warning('请输入 Git 仓库地址')
    return
  }
  creating.value = true
  try {
    await api.post('/projects', { name: form.value.name, git_url: form.value.git_url })
    ElMessage.success('项目创建成功')
    showCreateDialog.value = false
    form.value = { name: '', git_url: '' }
    loadProjects()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    creating.value = false
  }
}

const refreshProject = async (id) => {
  refreshingId.value = id
  try {
    await api.post(`/projects/${id}/refresh`)
    ElMessage.success('刷新成功')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    refreshingId.value = null
  }
}

const deleteProject = async (id) => {
  try {
    await api.delete(`/projects/${id}`)
    ElMessage.success('删除成功')
    loadProjects()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

const goDetail = (id) => router.push(`/projects/${id}`)

onMounted(loadProjects)
</script>

<style scoped>
.project-list {
  max-width: 1000px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 20px;
  color: #303133;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.project-card {
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  padding: 18px 20px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.project-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.project-icon {
  font-size: 22px;
  flex-shrink: 0;
}
.project-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-item {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #606266;
  min-width: 0;
}
.meta-label {
  flex-shrink: 0;
  width: 36px;
  color: #909399;
}
.meta-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 80px 0;
  color: #909399;
}
.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}
</style>
