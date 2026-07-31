<template>
  <div class="app-container vehicle-detail">
    <el-page-header @back="goBack"><template #content><span>{{ readonly ? '车辆详情' : form.vehicleId ? '修改车辆' : '新增车辆' }}</span></template></el-page-header>
    <el-form ref="vehicleRef" :disabled="readonly" :model="form" :rules="rules" label-width="110px" class="vehicle-form">
      <el-divider content-position="left">基础信息</el-divider>
      <el-row :gutter="18">
        <el-col :xs="24" :md="8"><el-form-item label="车牌号" prop="plateNo"><el-input v-model="form.plateNo" maxlength="20" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="车牌颜色" prop="plateColor"><el-select v-model="form.plateColor" class="w-full"><el-option v-for="item in truck_plate_color" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="所属中队" prop="deptId"><el-tree-select v-model="form.deptId" :data="deptOptions" check-strictly class="w-full" node-key="deptId" :props="deptProps" @change="handleDeptChange" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="车辆类型"><el-select v-model="form.vehicleType" clearable class="w-full"><el-option v-for="item in truck_vehicle_type" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="车辆品牌"><el-input v-model="form.vehicleBrand" /></el-form-item></el-col><el-col :xs="24" :md="8"><el-form-item label="车架号"><el-input v-model="form.vin" maxlength="17" /></el-form-item></el-col>
        <el-col :xs="24" :md="12"><el-form-item label="机动车所有人"><el-input v-model="form.motorOwnerName" /></el-form-item></el-col><el-col :xs="24" :md="12"><el-form-item label="来源"><el-select v-model="form.sourceType" clearable class="w-full"><el-option v-for="item in truck_source_type" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
        <el-col :xs="24" :md="12"><el-form-item label="保险情况"><el-input v-model="form.insuranceStatus" maxlength="100" /></el-form-item></el-col><el-col :xs="24" :md="12"><el-form-item label="保险公司及金额"><el-input v-model="form.insuranceInfo" maxlength="255" /></el-form-item></el-col>
      </el-row>
      <el-divider content-position="left">归属与人员</el-divider>
      <el-row :gutter="18"><el-col :xs="24" :md="8"><el-form-item label="归属主体"><el-select v-model="form.ownerId" :loading="ownerLoading" clearable filterable remote reserve-keyword class="w-full" placeholder="输入名称搜索主体" :remote-method="searchOwners" @change="handleOwnerChange"><el-option v-for="item in ownerOptions" :key="item.ownerId" :label="item.ownerName" :value="item.ownerId"><span>{{ item.ownerName }}</span><span class="owner-option">{{ item.deptName }}</span></el-option></el-select></el-form-item></el-col><el-col :xs="24" :md="8"><el-form-item label="驾驶员"><el-input v-model="form.driverName" /></el-form-item></el-col><el-col :xs="24" :md="8"><el-form-item label="驾驶员电话"><el-input v-model="form.driverPhone" /></el-form-item></el-col><el-col :xs="24" :md="12"><el-form-item label="挂靠公司"><el-input v-model="form.affiliatedCompany" /></el-form-item></el-col></el-row>
      <el-divider content-position="left">安全与照片</el-divider>
      <el-row :gutter="18"><el-col :xs="24" :md="8"><el-form-item label="车辆状态"><el-select v-model="form.vehicleStatus" class="w-full"><el-option v-for="item in truck_vehicle_status" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col><el-col :xs="24" :md="8"><el-form-item label="重点监管"><el-switch v-model="form.supervisionFlag" active-value="1" inactive-value="0" /></el-form-item></el-col><el-col :xs="24" :md="8"><el-form-item label="车辆照片"><BusinessFileUpload v-model="photoFiles" :disabled="readonly" :file-size="5" :file-type="['jpg','jpeg','png']" :is-show-tip="false" :limit="1" /></el-form-item></el-col></el-row>
      <el-form-item label="安全设备"><el-table :data="form.devices" border class="device-table"><el-table-column label="设备类型" min-width="180"><template #default="scope"><el-select v-model="scope.row.deviceType" class="w-full"><el-option v-for="item in truck_device_type" :key="item.value" :label="item.label" :value="item.value" /></el-select></template></el-table-column><el-table-column label="产品名称" min-width="150"><template #default="scope"><el-input v-model="scope.row.productName" /></template></el-table-column><el-table-column label="品牌" min-width="130"><template #default="scope"><el-input v-model="scope.row.brand" /></template></el-table-column><el-table-column label="安装日期" width="170"><template #default="scope"><el-date-picker v-model="scope.row.installDate" type="date" value-format="YYYY-MM-DD" /></template></el-table-column><el-table-column v-if="!readonly" label="操作" width="80"><template #default="scope"><el-button link type="danger" icon="Delete" @click="removeDevice(scope.$index)" /></template></el-table-column></el-table><el-button v-if="!readonly" class="mt8" icon="Plus" plain @click="addDevice">添加设备</el-button></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" :rows="3" type="textarea" /></el-form-item><el-form-item v-if="form.vehicleId && !readonly" label="归属变更原因"><el-input v-model="form.changeReason" maxlength="255" /></el-form-item>
      <el-form-item v-if="!readonly"><el-button type="primary" @click="submitForm">保存</el-button><el-button @click="goBack">取消</el-button></el-form-item>
    </el-form>
  </div>
</template>

<script setup name="TruckVehicleDetail">
import { getOwner, listOwner } from '@/api/truck/owner'
import { addVehicle, getVehicle, updateVehicle } from '@/api/truck/vehicle'
import { listDept } from '@/api/system/dept'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute(); const router = useRouter(); const { proxy } = getCurrentInstance()
const { truck_vehicle_type, truck_plate_color, truck_vehicle_status, truck_source_type, truck_device_type } = proxy.useDict('truck_vehicle_type', 'truck_plate_color', 'truck_vehicle_status', 'truck_source_type', 'truck_device_type')
const readonly = computed(() => route.query.readonly === '1'); const deptOptions = ref([]); const ownerOptions = ref([]); const ownerLoading = ref(false); const photoFiles = ref([])
const deptProps = { value: 'deptId', label: 'deptName', children: 'children' }
const form = ref({}); const rules = { plateNo: [{ required: true, message: '请输入车牌号', trigger: 'blur' }], plateColor: [{ required: true, message: '请选择车牌颜色', trigger: 'change' }], deptId: [{ required: true, message: '请选择所属中队', trigger: 'change' }] }
function reset() { form.value = { vehicleId: undefined, plateNo: undefined, plateColor: 'yellow', deptId: undefined, vehicleType: undefined, vehicleBrand: undefined, vin: undefined, sourceType: undefined, ownerId: undefined, motorOwnerName: undefined, insuranceStatus: undefined, insuranceInfo: undefined, driverName: undefined, driverPhone: undefined, affiliatedCompany: undefined, vehicleStatus: 'normal', supervisionFlag: '0', devices: [], remark: undefined, changeReason: undefined }; photoFiles.value = [] }
function addDevice() { form.value.devices.push({ deviceType: undefined, productName: undefined, brand: undefined, installDate: undefined, status: '0' }) }
function removeDevice(index) { form.value.devices.splice(index, 1) }
function searchOwners(keyword) { ownerLoading.value = true; listOwner({ pageNum: 1, pageSize: 50, ownerName: keyword, deptId: form.value.deptId }).then(response => { ownerOptions.value = response.rows }).finally(() => { ownerLoading.value = false }) }
function handleOwnerChange(ownerId) { const owner = ownerOptions.value.find(item => item.ownerId === ownerId); if (owner) { form.value.ownerType = owner.ownerType; form.value.motorOwnerName = form.value.motorOwnerName || owner.ownerName } }
function handleDeptChange() { if (form.value.ownerId) { form.value.ownerId = undefined; form.value.ownerType = undefined } }
function goBack() { router.push('/truck/vehicle') }
function submitForm() { proxy.$refs.vehicleRef.validate(valid => { if (!valid) return; const payload = { ...form.value, photoFileId: photoFiles.value[0]?.fileId || form.value.photoFileId || null }; const request = payload.vehicleId ? updateVehicle(payload) : addVehicle(payload); request.then(() => { proxy.$modal.msgSuccess(payload.vehicleId ? '修改成功' : '新增成功'); goBack() }) }) }
function loadDetail() { const vehicleId = route.params.vehicleId; if (!vehicleId) return; getVehicle(vehicleId).then(response => { form.value = response.data; if (form.value.ownerId) getOwner(form.value.ownerId).then(ownerResponse => { ownerOptions.value = [ownerResponse.data] }); if (form.value.photoFileId) photoFiles.value = [{ fileId: form.value.photoFileId, name: '车辆照片', url: `/common/files/${form.value.photoFileId}/download/车辆照片` }] }) }
listDept().then(response => { deptOptions.value = proxy.handleTree(response.data, 'deptId') }); reset(); loadDetail()
</script>

<style scoped>
.vehicle-form { max-width: 1180px; margin-top: 18px; }
.owner-option { float: right; color: var(--el-text-color-secondary); font-size: 12px; }
.device-table { width: 100%; }
.mt8 { margin-top: 8px; }
</style>
