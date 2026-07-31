<template>
  <div class="app-container">
    <el-form ref="queryRef" :inline="true" :model="queryParams" v-show="showSearch">
      <el-form-item label="车牌号" prop="plateNo">
        <el-input v-model="queryParams.plateNo" clearable placeholder="请输入车牌号" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="所属中队" prop="deptId">
        <el-tree-select v-model="queryParams.deptId" :data="deptOptions" check-strictly clearable node-key="deptId" placeholder="全部中队" :props="deptProps" />
      </el-form-item>
      <el-form-item label="车辆状态" prop="vehicleStatus">
        <el-select v-model="queryParams.vehicleStatus" clearable placeholder="全部状态">
          <el-option v-for="item in truck_vehicle_status" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="车辆来源" prop="sourceType">
        <el-select v-model="queryParams.sourceType" clearable placeholder="全部来源">
          <el-option v-for="item in truck_source_type" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="监管状态" prop="supervisionFlag">
        <el-select v-model="queryParams.supervisionFlag" clearable placeholder="全部车辆">
          <el-option label="重点监管" value="1" />
          <el-option label="非重点监管" value="0" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button icon="Search" type="primary" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5"><el-button v-hasPermi="['truck:vehicle:add']" icon="Plus" plain type="primary" @click="handleAdd">新增车辆</el-button></el-col>
      <el-col :span="1.5"><el-button v-hasPermi="['truck:vehicle:import']" icon="Upload" plain type="info" @click="openImport">批量导入</el-button></el-col>
      <el-col :span="1.5"><el-button v-hasPermi="['truck:vehicle:export']" icon="Download" plain type="warning" @click="handleExport">导出</el-button></el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <el-table v-loading="loading" :data="vehicleList">
      <el-table-column label="车牌号" min-width="130" prop="plateNo" />
      <el-table-column label="车牌颜色" width="110"><template #default="scope"><dict-tag :options="truck_plate_color" :value="scope.row.plateColor" /></template></el-table-column>
      <el-table-column label="车辆类型" min-width="125"><template #default="scope"><dict-tag :options="truck_vehicle_type" :value="scope.row.vehicleType" /></template></el-table-column>
      <el-table-column label="机动车所有人" min-width="150" prop="motorOwnerName" show-overflow-tooltip />
      <el-table-column label="所属中队" min-width="125"><template #default="scope">{{ getDeptName(scope.row.deptId) }}</template></el-table-column>
      <el-table-column label="来源" width="105"><template #default="scope"><dict-tag :options="truck_source_type" :value="scope.row.sourceType" /></template></el-table-column>
      <el-table-column label="预警" width="105">
        <template #default="scope">
          <el-tag v-if="scope.row.warningLevel === 'level_one'" type="danger">一级预警</el-tag>
          <el-tag v-else-if="scope.row.warningLevel === 'level_two'" type="warning">二级预警</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="105"><template #default="scope"><dict-tag :options="truck_vehicle_status" :value="scope.row.vehicleStatus" /></template></el-table-column>
      <el-table-column label="操作" fixed="right" width="165">
        <template #default="scope">
          <el-button link type="primary" icon="View" @click="openDetail(scope.row)">详情</el-button>
          <el-button v-hasPermi="['truck:vehicle:edit']" link type="primary" icon="Edit" @click="handleEdit(scope.row)">修改</el-button>
          <el-button v-hasPermi="['truck:vehicle:remove']" link type="danger" icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <pagination v-show="total > 0" v-model:limit="queryParams.pageSize" v-model:page="queryParams.pageNum" :total="total" @pagination="getList" />

    <el-dialog v-model="importDialog.open" title="车辆批量导入" width="520px" append-to-body @closed="resetImport">
      <div class="import-toolbar">
        <span>Excel 台账</span>
        <el-button link icon="Download" type="primary" @click="downloadTemplate">下载模板</el-button>
      </div>
      <el-upload ref="uploadRef" drag action="#" accept=".xlsx" :auto-upload="false" :limit="1" :on-change="handleFileChange" :on-remove="handleFileRemove">
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖放文件到此处，或<em>选择文件</em></div>
      </el-upload>
      <el-alert v-if="importDialog.result" class="import-result" :closable="false" :type="importDialog.result.errorCount ? 'warning' : 'success'" show-icon>
        <template #title>成功 {{ importDialog.result.successCount }} 行，失败 {{ importDialog.result.errorCount }} 行</template>
        <el-button v-if="importDialog.result.batchId" link type="danger" @click="downloadImportErrors">下载错误明细</el-button>
      </el-alert>
      <template #footer>
        <el-button @click="importDialog.open = false">关闭</el-button>
        <el-button type="primary" :loading="importDialog.uploading" :disabled="!importDialog.file" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="TruckVehicle">
import { delVehicle, importVehicle, listVehicle } from '@/api/truck/vehicle'
import { listDept } from '@/api/system/dept'
import download from '@/plugins/download'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { proxy } = getCurrentInstance()
const { truck_vehicle_type, truck_plate_color, truck_vehicle_status, truck_source_type } = proxy.useDict('truck_vehicle_type', 'truck_plate_color', 'truck_vehicle_status', 'truck_source_type')
const loading = ref(false)
const showSearch = ref(true)
const vehicleList = ref([])
const total = ref(0)
const deptOptions = ref([])
const deptList = ref([])
const deptProps = { value: 'deptId', label: 'deptName', children: 'children' }
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  plateNo: undefined,
  deptId: route.query.deptId ? Number(route.query.deptId) : undefined,
  vehicleStatus: undefined,
  sourceType: route.query.sourceType || undefined,
  supervisionFlag: route.query.supervisionFlag || undefined,
  warningLevel: route.query.warningLevel || undefined
})
const importDialog = reactive({ open: false, uploading: false, file: null, result: null })

function getList() {
  loading.value = true
  listVehicle(queryParams).then(response => {
    vehicleList.value = response.rows
    total.value = response.total
  }).finally(() => { loading.value = false })
}
function handleQuery() { queryParams.pageNum = 1; getList() }
function resetQuery() { proxy.resetForm('queryRef'); handleQuery() }
function handleAdd() { router.push('/truck/vehicle-detail') }
function handleEdit(row) { router.push(`/truck/vehicle-detail/${row.vehicleId}`) }
function openDetail(row) { router.push(`/truck/vehicle-detail/${row.vehicleId}?readonly=1`) }
function handleDelete(row) {
  proxy.$modal.confirm(`是否删除车辆“${row.plateNo}”？`)
    .then(() => delVehicle(row.vehicleId))
    .then(() => { proxy.$modal.msgSuccess('删除成功'); getList() })
    .catch(() => {})
}
function getDeptName(deptId) { return deptList.value.find(item => item.deptId === deptId)?.deptName || '-' }
function openImport() { importDialog.open = true }
function resetImport() {
  importDialog.file = null
  importDialog.result = null
  importDialog.uploading = false
  proxy.$refs.uploadRef?.clearFiles()
}
function handleFileChange(file) {
  importDialog.file = file.raw
  importDialog.result = null
}
function handleFileRemove() { importDialog.file = null }
function downloadTemplate() {
  proxy.download('/truck/vehicle/import-template', {}, `车辆导入模板_${Date.now()}.xlsx`)
}
function handleExport() {
  proxy.download('/truck/vehicle/export', queryParams, `车辆档案_${Date.now()}.xlsx`)
}
function downloadImportErrors() {
  download.file(`/truck/vehicle/import-error/${importDialog.result.batchId}`)
}
async function submitImport() {
  if (!importDialog.file?.name.toLowerCase().endsWith('.xlsx')) {
    proxy.$modal.msgError('请选择 xlsx 格式文件')
    return
  }
  importDialog.uploading = true
  try {
    const response = await importVehicle(importDialog.file)
    importDialog.result = response.data
    proxy.$modal.msgSuccess(response.msg)
    getList()
  } finally {
    importDialog.uploading = false
  }
}

listDept().then(response => {
  deptList.value = response.data
  deptOptions.value = proxy.handleTree(response.data, 'deptId')
})
getList()
</script>

<style scoped>
.import-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; color: #52606d; font-size: 14px; }
.import-result { margin-top: 16px; }
</style>
