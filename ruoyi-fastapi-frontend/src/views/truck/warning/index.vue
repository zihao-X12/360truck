<template>
  <div class="app-container warning-page">
    <el-form ref="queryRef" :inline="true" :model="queryParams" v-show="showSearch">
      <el-form-item label="车牌号" prop="plateNo">
        <el-input v-model="queryParams.plateNo" clearable placeholder="请输入车牌号" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="所属中队" prop="deptId">
        <el-tree-select v-model="queryParams.deptId" :data="deptOptions" check-strictly clearable node-key="deptId" placeholder="全部中队" :props="deptProps" />
      </el-form-item>
      <el-form-item label="预警等级" prop="warningLevel">
        <el-select v-model="queryParams.warningLevel" clearable placeholder="全部等级">
          <el-option label="一级预警" value="level_one" />
          <el-option label="二级预警" value="level_two" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button icon="Search" type="primary" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5"><el-button v-hasPermi="['truck:warning:recalculate']" icon="RefreshRight" plain type="primary" :loading="recalculating" @click="handleRecalculate">重新计算预警</el-button></el-col>
      <el-col :span="1.5"><el-button v-hasPermi="['truck:warning:export']" icon="Download" plain type="warning" @click="handleExport">导出预警</el-button></el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <el-table v-loading="loading" :data="warningList">
      <el-table-column label="预警等级" width="110">
        <template #default="scope"><el-tag :type="scope.row.warningLevel === 'level_one' ? 'danger' : 'warning'">{{ levelName(scope.row.warningLevel) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="车牌号" min-width="125" prop="plateNo" />
      <el-table-column label="所属中队" min-width="130" prop="deptName" />
      <el-table-column label="归属主体" min-width="170" prop="ownerName" show-overflow-tooltip />
      <el-table-column label="工地名称" min-width="160" prop="projectName" show-overflow-tooltip />
      <el-table-column label="缺失设备" min-width="230">
        <template #default="scope">
          <el-tag v-for="item in scope.row.missingDeviceTypes" :key="item" class="device-tag" type="danger" effect="plain">{{ deviceName(item) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="100">
        <template #default="scope"><el-button link icon="View" type="primary" @click="openVehicle(scope.row)">车辆详情</el-button></template>
      </el-table-column>
    </el-table>
    <pagination v-show="total > 0" v-model:limit="queryParams.pageSize" v-model:page="queryParams.pageNum" :total="total" @pagination="getList" />
  </div>
</template>

<script setup name="TruckWarning">
import { listWarning, recalculateWarning } from '@/api/truck/warning'
import { filterTruckSquads, listTruckDeptOptions } from '@/api/truck/dept'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { proxy } = getCurrentInstance()
const loading = ref(false)
const recalculating = ref(false)
const showSearch = ref(true)
const warningList = ref([])
const total = ref(0)
const deptOptions = ref([])
const deptProps = { value: 'deptId', label: 'deptName', children: 'children' }
const queryParams = reactive({ pageNum: 1, pageSize: 10, plateNo: undefined, deptId: undefined, warningLevel: route.query.warningLevel || undefined })

function levelName(level) { return level === 'level_one' ? '一级预警' : '二级预警' }
function deviceName(type) { return type === 'brake_assist' ? '刹车辅助系统' : type === 'panoramic_360' ? '360全景影像' : type }
function openVehicle(row) { router.push(`/truck/vehicle-detail/${row.vehicleId}?readonly=1`) }
function getList() {
  loading.value = true
  listWarning(queryParams).then(response => {
    warningList.value = response.rows || []
    total.value = response.total || 0
  }).finally(() => { loading.value = false })
}
function handleQuery() { queryParams.pageNum = 1; getList() }
function resetQuery() { proxy.resetForm('queryRef'); handleQuery() }
function handleExport() { proxy.download('/truck/warning/export', queryParams, `重点监管预警_${Date.now()}.xlsx`) }
function handleRecalculate() {
  proxy.$modal.confirm('将根据当前安全设备安装情况重新计算全部可管理车辆的预警，是否继续？').then(async () => {
    recalculating.value = true
    try {
      const response = await recalculateWarning()
      proxy.$modal.msgSuccess(response.msg)
      getList()
    } finally {
      recalculating.value = false
    }
  }).catch(() => {})
}

listTruckDeptOptions().then(response => { deptOptions.value = filterTruckSquads(proxy.handleTree(response.data, 'deptId')) })
getList()
</script>

<style scoped>
.warning-page .device-tag { margin: 2px 6px 2px 0; }
</style>
