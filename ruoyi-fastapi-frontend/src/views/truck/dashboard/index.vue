<template>
  <main class="business-dashboard" v-loading="loading">
    <header class="dashboard-header">
      <div>
        <h1>松阳大队大货车业务看板</h1>
        <p>车辆、归属主体、安全设备和重点监管实时概览</p>
      </div>
      <el-button icon="Refresh" @click="loadDashboard">刷新数据</el-button>
    </header>

    <section class="metric-grid" aria-label="业务指标">
      <button v-for="item in metrics" :key="item.label" class="metric-card" type="button" @click="router.push(item.path)">
        <span class="metric-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <span class="metric-note">{{ item.note }}</span>
        <span class="metric-accent" :class="item.tone" />
      </button>
    </section>

    <section class="dashboard-grid">
      <div class="data-panel dept-panel">
        <div class="panel-header">
          <div><h2>各中队业务分布</h2><span>点击车辆数查看对应中队车辆</span></div>
        </div>
        <el-table :data="deptStats" empty-text="暂无中队数据">
          <el-table-column label="中队" min-width="130" prop="deptName" />
          <el-table-column label="车辆" width="100" align="right">
            <template #default="scope"><el-button link type="primary" @click="openDept(scope.row)">{{ scope.row.vehicleCount }}</el-button></template>
          </el-table-column>
          <el-table-column label="运输企业" width="110" align="right" prop="enterpriseCount" />
          <el-table-column label="个人车主" width="110" align="right" prop="individualCount" />
        </el-table>
      </div>

      <div class="data-panel">
        <div class="panel-header">
          <div><h2>安全设备覆盖</h2><span>在管有效车辆安装情况</span></div>
        </div>
        <div v-for="item in deviceCoverage" :key="item.deviceType" class="coverage-item">
          <div class="coverage-title">
            <span>{{ item.deviceName }}</span>
            <strong>{{ item.installedCount }} / {{ item.vehicleTotal }}</strong>
          </div>
          <el-progress :percentage="item.coverageRate" :stroke-width="12" :color="progressColor(item.coverageRate)" />
        </div>
        <el-empty v-if="!deviceCoverage.length" :image-size="72" description="暂无设备统计" />
        <div class="warning-summary">
          <div><span>一级预警</span><strong class="danger">{{ summary.levelOneCount }}</strong></div>
          <div><span>二级预警</span><strong class="warning">{{ summary.levelTwoCount }}</strong></div>
          <el-button type="primary" plain @click="router.push('/truck/warning')">进入预警处置</el-button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup name="TruckDashboard">
import { getDashboardDeptStat, getDashboardDeviceCoverage, getDashboardSummary } from '@/api/truck/dashboard'
import { useRouter } from 'vue-router'

const router = useRouter()
const { proxy } = getCurrentInstance()
const loading = ref(false)
const summary = reactive({
  vehicleTotal: 0, localVehicleCount: 0, nonlocalVehicleCount: 0,
  ownerTotal: 0, enterpriseCount: 0, individualCount: 0,
  supervisionCount: 0, levelOneCount: 0, levelTwoCount: 0
})
const deptStats = ref([])
const deviceCoverage = ref([])

const metrics = computed(() => [
  { label: '车辆总数', value: summary.vehicleTotal, note: '辖区登记车辆', path: '/truck/vehicle', tone: 'blue' },
  { label: '本地车辆', value: summary.localVehicleCount, note: '本地来源车辆', path: '/truck/vehicle?sourceType=local', tone: 'green' },
  { label: '外地车辆', value: summary.nonlocalVehicleCount, note: '外地来源车辆', path: '/truck/vehicle?sourceType=nonlocal', tone: 'gray' },
  { label: '归属主体', value: summary.ownerTotal, note: `企业 ${summary.enterpriseCount} · 个人 ${summary.individualCount}`, path: '/truck/owner', tone: 'cyan' },
  { label: '重点监管', value: summary.supervisionCount, note: '存在安全设备缺装', path: '/truck/warning', tone: 'amber' },
  { label: '一级预警', value: summary.levelOneCount, note: '需优先处置', path: '/truck/warning?warningLevel=level_one', tone: 'red' },
  { label: '二级预警', value: summary.levelTwoCount, note: '需跟进整改', path: '/truck/warning?warningLevel=level_two', tone: 'orange' }
])

function openDept(row) { router.push({ path: '/truck/vehicle', query: { deptId: row.deptId } }) }
function progressColor(rate) { return rate >= 90 ? '#23875b' : rate >= 60 ? '#d6921e' : '#c94b45' }

async function loadDashboard() {
  loading.value = true
  try {
    const [summaryResponse, deptResponse, coverageResponse] = await Promise.all([
      getDashboardSummary(), getDashboardDeptStat(), getDashboardDeviceCoverage()
    ])
    Object.assign(summary, summaryResponse.data)
    deptStats.value = deptResponse.data || []
    deviceCoverage.value = coverageResponse.data || []
  } catch {
    proxy.$modal.msgError('业务看板数据加载失败')
  } finally {
    loading.value = false
  }
}

loadDashboard()
</script>

<style scoped>
.business-dashboard { min-height: calc(100vh - 84px); padding: 24px; background: #f4f6f8; color: #1f2933; }
.dashboard-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.dashboard-header h1 { margin: 0 0 6px; font-size: 24px; line-height: 1.3; letter-spacing: 0; }
.dashboard-header p, .panel-header span { margin: 0; color: #6b7280; font-size: 13px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.metric-card { position: relative; min-height: 124px; padding: 18px; overflow: hidden; text-align: left; background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; cursor: pointer; }
.metric-card:hover { border-color: #9aa7b2; box-shadow: 0 5px 16px rgb(31 41 51 / 8%); }
.metric-label { display: block; color: #52606d; font-size: 14px; }
.metric-card strong { display: block; margin: 10px 0 5px; font-size: 30px; line-height: 1; letter-spacing: 0; }
.metric-note { color: #88929d; font-size: 12px; }
.metric-accent { position: absolute; inset: 0 auto 0 0; width: 4px; }
.metric-accent.green { background: #23875b; }.metric-accent.blue { background: #2878b5; }.metric-accent.gray { background: #667784; }
.metric-accent.cyan { background: #16838f; }.metric-accent.amber { background: #d6921e; }.metric-accent.orange { background: #c86c24; }.metric-accent.red { background: #c94b45; }
.dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, .8fr); gap: 18px; }
.data-panel { min-width: 0; padding: 18px; background: #fff; border: 1px solid #e3e8ee; border-radius: 6px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.panel-header h2 { margin: 0 0 4px; font-size: 16px; letter-spacing: 0; }
.coverage-item { margin: 20px 0 26px; }
.coverage-title { display: flex; justify-content: space-between; margin-bottom: 9px; font-size: 14px; }
.coverage-title strong { color: #52606d; }
.warning-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding-top: 18px; border-top: 1px solid #e8edf1; }
.warning-summary > div { display: flex; align-items: baseline; justify-content: space-between; padding: 12px; background: #f7f9fa; }
.warning-summary strong { font-size: 22px; }.warning-summary .danger { color: #c94b45; }.warning-summary .warning { color: #c86c24; }
.warning-summary .el-button { grid-column: 1 / -1; margin: 4px 0 0; }
@media (max-width: 1100px) { .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.dashboard-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .business-dashboard { padding: 14px; }.dashboard-header { align-items: flex-start; gap: 12px; }.dashboard-header h1 { font-size: 20px; }.metric-grid { grid-template-columns: 1fr 1fr; gap: 10px; }.metric-card { min-height: 116px; padding: 15px; }.metric-card strong { font-size: 26px; }.dashboard-grid { display: block; }.data-panel + .data-panel { margin-top: 14px; } }
</style>
