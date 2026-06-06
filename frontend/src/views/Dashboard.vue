<template>
  <div class="dashboard-container">
    <!-- 核心指标卡片 -->
    <el-row :gutter="20">
      <!-- 当前告警 -->
      <el-col :span="6">
        <el-card class="stat-card" :class="{ 'has-alert': stats.current_alerts > 0 }"
                 @click="$router.push('/alerts/current')" style="cursor: pointer">
          <div class="stat-header">
            <span class="stat-label">当前告警</span>
            <el-icon :size="24" :color="stats.current_alerts > 0 ? '#F56C6C' : '#67C23A'">
              <Bell />
            </el-icon>
          </div>
          <div class="stat-value" :style="{ color: stats.current_alerts > 0 ? '#F56C6C' : '#67C23A' }">
            {{ stats.current_alerts }}
          </div>
          <div class="stat-sub stat-sub-placeholder" aria-hidden="true">&nbsp;</div>
        </el-card>
      </el-col>

      <!-- 今日告警 -->
      <el-col :span="6">
        <el-card class="stat-card" @click="$router.push('/alerts/history')" style="cursor: pointer">
          <div class="stat-header">
            <span class="stat-label">今日告警</span>
            <el-icon :size="24" color="#E6A23C">
              <Warning />
            </el-icon>
          </div>
          <div class="stat-value" style="color: #E6A23C">
            {{ stats.today_alerts }}
          </div>
          <div class="stat-sub">昨日 {{ stats.yesterday_alerts }} 条</div>
        </el-card>
      </el-col>

      <!-- 今日执行 -->
      <el-col :span="6">
        <el-card class="stat-card" @click="$router.push('/automation/executions')" style="cursor: pointer">
          <div class="stat-header">
            <span class="stat-label">今日执行</span>
            <el-icon :size="24" color="#409EFF">
              <VideoPlay />
            </el-icon>
          </div>
          <div class="stat-value" style="color: #409EFF">
            {{ stats.executions.total }}
          </div>
          <div class="stat-sub">
            <span v-if="stats.executions.total > 0">
              成功 {{ stats.executions.success }}
              <span style="color: #F56C6C" v-if="stats.executions.failed > 0"> · 失败 {{ stats.executions.failed }}</span>
              · 成功率 {{ stats.executions.success_rate }}%
            </span>
            <span v-else>今日暂无执行</span>
          </div>
        </el-card>
      </el-col>

      <!-- 活跃定时任务 -->
      <el-col :span="6">
        <el-card class="stat-card" @click="$router.push('/automation/scheduled-tasks')" style="cursor: pointer">
          <div class="stat-header">
            <span class="stat-label">活跃定时任务</span>
            <el-icon :size="24" color="#9C27B0">
              <Clock />
            </el-icon>
          </div>
          <div class="stat-value" style="color: #9C27B0">
            {{ stats.scheduled_tasks.active }}
          </div>
          <div class="stat-sub">共 {{ stats.scheduled_tasks.total }} 个任务</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>告警趋势（近7天）</span>
          </template>
          <div ref="alertTrendChart" style="height: 300px"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>告警级别分布（近7天）</span>
          </template>
          <div ref="severityChart" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 服务器健康状态 -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>服务器资源使用 Top 5</span>
              <el-button text type="primary" @click="$router.push('/servers')">
                查看更多 →
              </el-button>
            </div>
          </template>
          <el-table :data="topServers" v-loading="loading" style="width: 100%">
            <el-table-column label="主机名" min-width="120">
              <template #default="{ row }">
                <div style="display: flex; align-items: center;">
                  <el-icon v-if="row.cpu_usage > 80 || row.memory_usage > 80 || row.disk_usage > 80" 
                           color="#E6A23C" style="margin-right: 5px">
                    <Warning />
                  </el-icon>
                  <el-icon v-else color="#67C23A" style="margin-right: 5px">
                    <CircleCheck />
                  </el-icon>
                  {{ row.hostname }}
                </div>
              </template>
            </el-table-column>
            <el-table-column label="IP地址" min-width="120" prop="ip_address" />
            <el-table-column label="CPU使用率" min-width="180">
              <template #default="{ row }">
                <el-progress 
                  :percentage="row.cpu_usage" 
                  :color="getProgressColor(row.cpu_usage)"
                  :format="(percentage) => `${percentage.toFixed(1)}%`"
                />
              </template>
            </el-table-column>
            <el-table-column label="内存使用率" min-width="180">
              <template #default="{ row }">
                <el-progress 
                  :percentage="row.memory_usage" 
                  :color="getProgressColor(row.memory_usage)"
                  :format="(percentage) => `${percentage.toFixed(1)}%`"
                />
              </template>
            </el-table-column>
            <el-table-column label="磁盘使用率" min-width="180">
              <template #default="{ row }">
                <el-progress 
                  :percentage="row.disk_usage" 
                  :color="getProgressColor(row.disk_usage)"
                  :format="(percentage) => `${percentage.toFixed(1)}%`"
                />
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && topServers.length === 0" description="暂无服务器数据" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近执行记录 -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近执行记录</span>
              <el-button text type="primary" @click="$router.push('/automation/executions')">
                查看全部 →
              </el-button>
            </div>
          </template>
          <el-table :data="recentExecutions" v-loading="loading" max-height="300" style="width: 100%">
            <el-table-column label="脚本" min-width="100">
              <template #default="{ row }">
                {{ getScriptName(row.script_id) }}
              </template>
            </el-table-column>
            <el-table-column label="服务器" min-width="100">
              <template #default="{ row }">
                {{ getServerName(row.server_id) }}
              </template>
            </el-table-column>
            <el-table-column label="类型" min-width="80">
              <template #default="{ row }">
                <el-tag v-if="row.execution_type === 'manual'" type="primary" size="small">手动</el-tag>
                <el-tag v-else type="success" size="small">定时</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" min-width="80">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'success'" type="success" size="small">成功</el-tag>
                <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
                <el-tag v-else type="info" size="small">运行中</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" min-width="150">
              <template #default="{ row }">
                {{ formatDate(row.started_at) }}
              </template>
            </el-table-column>
            <el-table-column label="结束时间" min-width="150">
              <template #default="{ row }">
                {{ formatDate(row.finished_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && recentExecutions.length === 0" description="暂无执行记录" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getDashboardStats, getRecentExecutions, getTopServers } from '@/api/dashboard'
import { getScripts } from '@/api/scripts'
import { getServers } from '@/api/servers'
import * as echarts from 'echarts'
import { SEVERITY_CHART_COLORS, SEVERITY_LABELS } from '@/utils/alertSeverity'

// 数据
const loading = ref(false)
const stats = reactive({
  current_alerts: 0,
  today_alerts: 0,
  yesterday_alerts: 0,
  executions: {
    total: 0,
    success: 0,
    failed: 0,
    success_rate: null
  },
  scheduled_tasks: {
    active: 0,
    total: 0
  },
  alert_trend: [],
  severity_distribution: {
    level1: 0,
    level2: 0,
    level3: 0,
    level4: 0
  }
})

const recentExecutions = ref([])
const topServers = ref([])
const scripts = ref([])
const servers = ref([])

const alertTrendChart = ref(null)
const severityChart = ref(null)

// 方法
const fetchStats = async () => {
  try {
    const response = await getDashboardStats()
    Object.assign(stats, response.data)
    
    // 渲染图表
    await nextTick()
    renderAlertTrendChart()
    renderSeverityChart()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const fetchRecentExecutions = async () => {
  try {
    const response = await getRecentExecutions()
    recentExecutions.value = response.data
  } catch (error) {
    console.error('获取最近执行失败:', error)
  }
}

const fetchTopServers = async () => {
  try {
    const response = await getTopServers()
    topServers.value = response.data
  } catch (error) {
    console.error('获取服务器数据失败:', error)
  }
}

const fetchScripts = async () => {
  try {
    const response = await getScripts({ page: 1, page_size: 100 })
    scripts.value = response.data.items
  } catch (error) {
    // 静默失败
  }
}

const fetchServers = async () => {
  try {
    const response = await getServers({ page: 1, page_size: 100 })
    servers.value = response.data.items
  } catch (error) {
    // 静默失败
  }
}

const renderAlertTrendChart = () => {
  if (!alertTrendChart.value) return
  
  const chart = echarts.init(alertTrendChart.value)
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: stats.alert_trend.map(item => item.date),
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [{
      data: stats.alert_trend.map(item => item.count),
      type: 'line',
      smooth: true,
      areaStyle: {
        color: 'rgba(64, 158, 255, 0.2)'
      },
      itemStyle: {
        color: '#409EFF'
      }
    }]
  }
  chart.setOption(option)
  
  // 响应式
  window.addEventListener('resize', () => chart.resize())
}

const renderSeverityChart = () => {
  if (!severityChart.value) return
  
  const chart = echarts.init(severityChart.value)
  
  // 计算总数
  const total = stats.severity_distribution.level1 + 
                stats.severity_distribution.level2 + 
                stats.severity_distribution.level3 + 
                stats.severity_distribution.level4
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center'
    },
    series: [{
      type: 'pie',
      radius: '60%',
      data: [
        { value: stats.severity_distribution.level1, name: SEVERITY_LABELS.level1, itemStyle: { color: SEVERITY_CHART_COLORS.level1 } },
        { value: stats.severity_distribution.level2, name: SEVERITY_LABELS.level2, itemStyle: { color: SEVERITY_CHART_COLORS.level2 } },
        { value: stats.severity_distribution.level3, name: SEVERITY_LABELS.level3, itemStyle: { color: SEVERITY_CHART_COLORS.level3 } },
        { value: stats.severity_distribution.level4, name: SEVERITY_LABELS.level4, itemStyle: { color: SEVERITY_CHART_COLORS.level4 } }
      ].filter(item => item.value > 0), // 只显示有数据的级别
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      label: {
        show: total > 0 // 有数据时显示标签
      }
    }]
  }
  
  // 如果没有数据，显示空状态
  if (total === 0) {
    option.title = {
      text: '暂无告警数据',
      left: 'center',
      top: 'center',
      textStyle: {
        color: '#909399',
        fontSize: 14
      }
    }
  }
  
  chart.setOption(option)
  
  // 响应式
  window.addEventListener('resize', () => chart.resize())
}

const getScriptName = (scriptId) => {
  const script = scripts.value.find(s => s.id === scriptId)
  return script ? script.name : '未知'
}

const getServerName = (serverId) => {
  const server = servers.value.find(s => s.id === serverId)
  return server ? server.hostname : '未知'
}

const getProgressColor = (percentage) => {
  if (percentage >= 90) return '#F56C6C'
  if (percentage >= 80) return '#E6A23C'
  return '#67C23A'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

// 刷新所有数据（不显示全屏 loading，避免图表闪烁）
const refreshAll = async () => {
  await Promise.all([
    fetchStats(),
    fetchScripts(),
    fetchServers(),
    fetchRecentExecutions(),
    fetchTopServers()
  ])
}

let autoRefreshTimer = null

// 生命周期
onMounted(async () => {
  loading.value = true
  try {
    await refreshAll()
  } finally {
    loading.value = false
  }

  autoRefreshTimer = setInterval(refreshAll, 60000)
})

onUnmounted(() => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 0;
}

.stat-card {
  cursor: pointer;
  min-height: 130px;
}

.stat-card.has-alert {
  border-left: 4px solid #F56C6C;
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  line-height: 1;
}

.stat-sub {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  min-height: 18px;
}

.stat-sub-placeholder {
  visibility: hidden;
  user-select: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
