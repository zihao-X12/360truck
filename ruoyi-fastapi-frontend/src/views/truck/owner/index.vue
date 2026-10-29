<template>
  <div class="app-container">
    <el-form ref="queryRef" :inline="true" :model="queryParams" v-show="showSearch">
      <el-form-item label="主体名称" prop="ownerName">
        <el-input v-model="queryParams.ownerName" clearable placeholder="企业或个人姓名" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="主体类型" prop="ownerType">
        <el-select v-model="queryParams.ownerType" clearable placeholder="全部类型">
          <el-option v-for="item in truck_owner_type" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="所属中队" prop="deptId">
        <el-tree-select v-model="queryParams.deptId" :data="deptOptions" check-strictly clearable node-key="deptId" placeholder="全部中队" :props="deptProps" />
      </el-form-item>
      <el-form-item>
        <el-button icon="Search" type="primary" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5"><el-button v-hasPermi="['truck:owner:add']" icon="Plus" plain type="primary" @click="handleAdd">新增主体</el-button></el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <el-table v-loading="loading" :data="ownerList">
      <el-table-column label="主体名称" min-width="180" prop="ownerName" show-overflow-tooltip />
      <el-table-column label="类型" width="120"><template #default="scope"><dict-tag :options="truck_owner_type" :value="scope.row.ownerType" /></template></el-table-column>
      <el-table-column label="登记归属中队" min-width="140">
        <template #header>
          <span>登记归属中队</span>
          <el-tooltip content="主体的登记归属，仅用于登记统计与筛选。挂靠车辆按车辆自己所属的中队分管，两者可以不同。" placement="top">
            <el-icon style="margin-left: 4px; vertical-align: middle"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>
        <template #default="scope">{{ getDeptName(scope.row.deptId) }}</template>
      </el-table-column>
      <el-table-column label="联系人" min-width="110" prop="contactName" />
      <el-table-column label="联系电话" min-width="130" prop="contactPhone" />
      <el-table-column label="名下车辆" width="105" align="center">
        <template #header>
          <span>名下车辆</span>
          <el-tooltip content="该主体名下全部车辆，包含其他中队分管的挂靠车辆。" placement="top">
            <el-icon style="margin-left: 4px; vertical-align: middle"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>
        <template #default="scope">
          <el-button link type="primary" icon="Van" @click="handleVehicles(scope.row)">{{ scope.row.vehicleCount || 0 }} 辆</el-button>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90"><template #default="scope"><dict-tag :options="sys_normal_disable" :value="scope.row.status" /></template></el-table-column>
      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="235">
        <template #default="scope">
          <el-button link type="primary" icon="View" @click="handleVehicles(scope.row)">查看车辆</el-button>
          <el-button v-hasPermi="['truck:owner:edit']" link type="primary" icon="Edit" @click="handleUpdate(scope.row)">修改</el-button>
          <el-button v-hasPermi="['truck:owner:remove']" link type="danger" icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <pagination v-show="total > 0" v-model:limit="queryParams.pageSize" v-model:page="queryParams.pageNum" :total="total" @pagination="getList" />

    <el-dialog v-model="open" :title="title" width="680px" append-to-body>
      <el-form ref="ownerRef" :model="form" :rules="rules" label-width="108px">
        <el-row :gutter="18">
          <el-col :span="12"><el-form-item label="主体类型" prop="ownerType"><el-select v-model="form.ownerType" class="w-full"><el-option v-for="item in truck_owner_type" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item prop="deptId">
              <template #label>
                <span>登记归属中队</span>
                <el-tooltip content="主体的登记归属，不决定名下车辆的分管中队。" placement="top">
                  <el-icon style="margin-left: 4px; vertical-align: middle"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-tree-select v-model="form.deptId" :data="deptOptions" check-strictly class="w-full" node-key="deptId" :props="deptProps" />
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item :label="form.ownerType === 'enterprise' ? '企业名称' : '车主姓名'" prop="ownerName"><el-input v-model="form.ownerName" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item v-if="form.ownerType === 'enterprise'" label="统一社会信用代码"><el-input v-model="form.creditCode" /></el-form-item><el-form-item v-else label="身份证号"><el-input v-model="form.idCardNo" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系人"><el-input v-model="form.contactName" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话"><el-input v-model="form.contactPhone" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="地址"><el-input v-model="form.address" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-radio-group v-model="form.status"><el-radio value="0">正常</el-radio><el-radio value="1">停用</el-radio></el-radio-group></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.remark" :rows="3" type="textarea" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="cancel">取消</el-button><el-button type="primary" @click="submitForm">确定</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup name="TruckOwner">
import { addOwner, delOwner, getOwner, listOwner, updateOwner } from '@/api/truck/owner'
import { filterTruckSquads, listTruckDeptOptions } from '@/api/truck/dept'
import useUserStore from '@/store/modules/user'
import { useRouter } from 'vue-router'

const { proxy } = getCurrentInstance()
const router = useRouter()
const userStore = useUserStore()
const { truck_owner_type, sys_normal_disable } = proxy.useDict('truck_owner_type', 'sys_normal_disable')
const loading = ref(false)
const showSearch = ref(true)
const open = ref(false)
const title = ref('')
const ownerList = ref([])
const total = ref(0)
const deptOptions = ref([])
const deptList = ref([])
const deptProps = { value: 'deptId', label: 'deptName', children: 'children' }
const queryParams = reactive({ pageNum: 1, pageSize: 10, ownerName: undefined, ownerType: undefined, deptId: undefined })
const form = ref({})
const rules = { ownerType: [{ required: true, message: '请选择主体类型', trigger: 'change' }], ownerName: [{ required: true, message: '请输入主体名称', trigger: 'blur' }], deptId: [{ required: true, message: '请选择所属中队', trigger: 'change' }] }

function getDeptOptions() { listTruckDeptOptions().then(response => { deptList.value = response.data; deptOptions.value = filterTruckSquads(proxy.handleTree(response.data, 'deptId')) }) }
function getDeptName(deptId) { return deptList.value.find(item => item.deptId === deptId)?.deptName || '-' }
function getList() { loading.value = true; listOwner(queryParams).then(response => { ownerList.value = response.rows; total.value = response.total }).finally(() => { loading.value = false }) }
function reset() { form.value = { ownerId: undefined, ownerType: 'enterprise', ownerName: undefined, creditCode: undefined, idCardNo: undefined, deptId: userStore.deptId, contactName: undefined, contactPhone: undefined, address: undefined, status: '0', remark: undefined }; proxy.resetForm('ownerRef') }
function cancel() { open.value = false; reset() }
function handleQuery() { queryParams.pageNum = 1; getList() }
function resetQuery() { proxy.resetForm('queryRef'); handleQuery() }
function handleAdd() { reset(); open.value = true; title.value = '新增主体' }
function handleUpdate(row) { reset(); getOwner(row.ownerId).then(response => { form.value = response.data; open.value = true; title.value = '修改主体' }) }
function handleVehicles(row) { router.push({ path: '/truck/vehicle', query: { ownerId: row.ownerId, ownerName: row.ownerName } }) }
function handleDelete(row) { proxy.$modal.confirm(`是否删除主体“${row.ownerName}”？`).then(() => delOwner(row.ownerId)).then(() => { proxy.$modal.msgSuccess('删除成功'); getList() }).catch(() => {}) }
function submitForm() { proxy.$refs.ownerRef.validate(valid => { if (!valid) return; const request = form.value.ownerId ? updateOwner(form.value) : addOwner(form.value); request.then(() => { proxy.$modal.msgSuccess(form.value.ownerId ? '修改成功' : '新增成功'); open.value = false; getList() }) }) }

getDeptOptions()
getList()
</script>
