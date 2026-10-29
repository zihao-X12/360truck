<template>
  <div class="app-container pass-record-page">
    <el-form ref="queryRef" :inline="true" :model="queryParams" v-show="showSearch">
      <el-form-item label="车牌号" prop="plateNo">
        <el-input v-model="queryParams.plateNo" clearable placeholder="请输入车牌号" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="过车时间" prop="passTimeRange">
        <el-date-picker v-model="passTimeRange" type="datetimerange" value-format="YYYY-MM-DD HH:mm:ss" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" />
      </el-form-item>
      <el-form-item label="设备编码" prop="deviceId">
        <el-input v-model="queryParams.deviceId" clearable placeholder="请输入设备编码" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="车辆归属" prop="vehicleMatched">
        <el-select v-model="queryParams.vehicleMatched" clearable placeholder="全部">
          <el-option label="本平台车辆" :value="true" />
          <el-option label="非本平台车辆" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button icon="Search" type="primary" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button v-hasPermi="['truck:passrecord:export']" icon="Download" plain type="warning" @click="handleExport">导出</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <el-table v-loading="loading" :data="passRecordList">
      <el-table-column label="车牌号" min-width="125" prop="plateNo">
        <template #default="scope">
          <el-link v-if="scope.row.vehicleMatched" type="primary" @click="openVehicle(scope.row)">{{ scope.row.plateNo }}</el-link>
          <span v-else>{{ scope.row.plateNo }}</span>
        </template>
      </el-table-column>
      <el-table-column label="车牌颜色" width="90">
        <template #default="scope">
          <el-tag v-if="scope.row.plateColor" effect="plain">{{ plateColorName(scope.row.plateColor) }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="车辆类型" min-width="110" prop="vehicleClass" />
      <el-table-column label="过车时间" min-width="160" prop="passTime" />
      <el-table-column label="经过道路" min-width="140" prop="nameOfPassedRoad" show-overflow-tooltip />
      <el-table-column label="车道/车速" width="100">
        <template #default="scope">{{ scope.row.laneNo ?? '-' }} 道 {{ scope.row.speed ?? '-' }}km/h</template>
      </el-table-column>
      <el-table-column label="卡口编号" min-width="170" prop="tollgateId" show-overflow-tooltip />
      <el-table-column label="所属中队" min-width="110" prop="deptName" />
      <el-table-column label="照片" width="100">
        <template #default="scope">
          <el-image v-if="scope.row.storageUrl1" :preview-src-list="[scope.row.storageUrl1]" :src="scope.row.storageUrl1" fit="cover" style="width: 48px; height: 48px; border-radius: 4px" />
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
    <pagination v-show="total > 0" v-model:limit="queryParams.pageSize" v-model:page="queryParams.pageNum" :total="total" @pagination="getList" />
  </div>
</template>

<script setup name="TruckPassRecord">
import { listPassRecord } from '@/api/truck/passRecord'
import { useRouter } from 'vue-router'

const router = useRouter()
const { proxy } = getCurrentInstance()
const loading = ref(false)
const showSearch = ref(true)
const passRecordList = ref([])
const total = ref(0)
const passTimeRange = ref([])
// GA/T1400 色号（标准 B.3.4）：1黑 2白 5蓝 6黄 9绿 99其他
const PLATE_COLOR_NAMES = { 1: '黑色', 2: '白色', 3: '灰色', 4: '红色', 5: '蓝色', 6: '黄色', 7: '橙色', 8: '棕色', 9: '绿色', 10: '紫色', 11: '青色', 12: '粉色', 13: '透明', 99: '其他' }
const queryParams = reactive({ pageNum: 1, pageSize: 10, plateNo: undefined, deviceId: undefined, vehicleMatched: undefined, startTime: undefined, endTime: undefined })

function plateColorName(code) { return PLATE_COLOR_NAMES[code] || code }

function getList() {
  loading.value = true
  queryParams.startTime = passTimeRange.value?.[0]
  queryParams.endTime = passTimeRange.value?.[1]
  listPassRecord(queryParams).then(response => {
    passRecordList.value = response.rows || []
    total.value = response.total || 0
  }).finally(() => { loading.value = false })
}
function handleQuery() { queryParams.pageNum = 1; getList() }
function resetQuery() { passTimeRange.value = []; proxy.resetForm('queryRef'); handleQuery() }
function handleExport() { proxy.download('/truck/passrecord/export', queryParams, `过车记录_${Date.now()}.xlsx`) }
function openVehicle(row) { router.push(`/truck/vehicle-detail/${row.vehicleId}?readonly=1`) }

getList()
</script>
