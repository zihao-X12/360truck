<template>
  <div class="app-container user-management">
    <aside class="org-panel">
      <div class="panel-title">所属单位</div>
      <el-tree
        ref="deptTreeRef"
        :data="deptOptions"
        :props="{ label: 'label', children: 'children' }"
        :expand-on-click-node="false"
        node-key="id"
        highlight-current
        default-expand-all
        @node-click="handleNodeClick"
      />
    </aside>

    <main class="user-content">
      <el-form ref="queryRef" :inline="true" :model="queryParams" v-show="showSearch">
        <el-form-item label="姓名" prop="nickName">
          <el-input v-model="queryParams.nickName" clearable placeholder="请输入姓名" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="登录账号" prop="userName">
          <el-input v-model="queryParams.userName" clearable placeholder="请输入登录账号" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="手机号" prop="phonenumber">
          <el-input v-model="queryParams.phonenumber" clearable placeholder="请输入手机号" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="queryParams.status" clearable placeholder="全部状态">
            <el-option v-for="item in sys_normal_disable" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="10" class="mb8">
        <el-col :span="1.5">
          <el-button v-hasPermi="['system:user:add']" type="primary" plain icon="Plus" @click="handleAdd">新增账号</el-button>
        </el-col>
        <el-col :span="1.5">
          <el-button v-hasPermi="['system:user:remove']" type="danger" plain icon="Delete" :disabled="!ids.length" @click="handleDelete()">批量删除</el-button>
        </el-col>
        <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
      </el-row>

      <el-table v-loading="loading" :data="userList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" align="center" :selectable="row => row.userId !== 1" />
        <el-table-column label="姓名" prop="nickName" min-width="120" show-overflow-tooltip />
        <el-table-column label="登录账号" prop="userName" min-width="140" show-overflow-tooltip />
        <el-table-column label="所属单位" prop="dept.deptName" min-width="130" show-overflow-tooltip />
        <el-table-column label="平台角色" min-width="135">
          <template #default="scope">
            <el-tag v-for="role in scope.row.roles" :key="role.roleId" class="role-tag" effect="plain">
              {{ roleLabel(role) }}
            </el-tag>
            <span v-if="!scope.row.roles?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="手机号" prop="phonenumber" width="125">
          <template #default="scope">{{ scope.row.phonenumber || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <el-switch
              v-model="scope.row.status"
              :disabled="scope.row.userId === 1"
              active-value="0"
              inactive-value="1"
              @change="handleStatusChange(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="165">
          <template #default="scope">{{ scope.row.loginDate ? parseTime(scope.row.loginDate) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="138" align="center">
          <template #default="scope">
            <template v-if="scope.row.userId !== 1">
              <el-tooltip content="修改" placement="top">
                <el-button v-hasPermi="['system:user:edit']" link type="primary" icon="Edit" @click="handleUpdate(scope.row)" />
              </el-tooltip>
              <el-tooltip content="重置密码" placement="top">
                <el-button v-hasPermi="['system:user:resetPwd']" link type="primary" icon="Key" @click="handleResetPwd(scope.row)" />
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button v-hasPermi="['system:user:remove']" link type="danger" icon="Delete" @click="handleDelete(scope.row)" />
              </el-tooltip>
            </template>
            <el-tag v-else type="info" effect="plain">系统管理员</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <pagination v-show="total > 0" v-model:limit="queryParams.pageSize" v-model:page="queryParams.pageNum" :total="total" @pagination="getList" />
    </main>

    <el-dialog v-model="open" :title="title" width="640px" append-to-body @closed="reset">
      <el-form ref="userRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="18">
          <el-col :xs="24" :sm="12">
            <el-form-item label="姓名" prop="nickName">
              <el-input v-model="form.nickName" maxlength="30" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="所属单位" prop="deptId">
              <el-tree-select
                v-model="form.deptId"
                :data="enabledDeptOptions"
                :props="{ value: 'id', label: 'label', children: 'children' }"
                value-key="id"
                check-strictly
                placeholder="请选择大队或中队"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="登录账号" prop="userName">
              <el-input v-model="form.userName" :disabled="Boolean(form.userId)" maxlength="30" placeholder="请输入登录账号" />
            </el-form-item>
          </el-col>
          <el-col v-if="!form.userId" :xs="24" :sm="12">
            <el-form-item label="初始密码" prop="password">
              <el-input v-model="form.password" maxlength="20" show-password type="password" placeholder="请输入初始密码" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="手机号" prop="phonenumber">
              <el-input v-model="form.phonenumber" maxlength="11" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="平台角色" prop="roleId">
              <el-select v-model="form.roleId" placeholder="请选择平台角色" class="w-full">
                <el-option v-for="role in roleOptions" :key="role.roleId" :label="roleLabel(role)" :value="role.roleId" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="账号状态">
              <el-radio-group v-model="form.status">
                <el-radio v-for="item in sys_normal_disable" :key="item.value" :value="item.value">{{ item.label }}</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="open = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="User">
import { addUser, changeUserStatus, delUser, deptTreeSelect, getUser, listUser, resetUserPwd, updateUser } from '@/api/system/user'

const BRIGADE_DEPT_ID = 9100
const PLATFORM_ROLE_IDS = [9010, 9011]
const { proxy } = getCurrentInstance()
const { sys_normal_disable } = proxy.useDict('sys_normal_disable')

const deptTreeRef = ref()
const userList = ref([])
const deptOptions = ref([])
const enabledDeptOptions = ref([])
const roleOptions = ref([])
const ids = ref([])
const loading = ref(false)
const showSearch = ref(true)
const open = ref(false)
const title = ref('')
const total = ref(0)
const initPassword = ref('admin123')

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    deptId: BRIGADE_DEPT_ID,
    nickName: undefined,
    userName: undefined,
    phonenumber: undefined,
    status: undefined
  },
  rules: {
    nickName: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
    deptId: [{ required: true, message: '所属单位不能为空', trigger: 'change' }],
    roleId: [{ required: true, message: '平台角色不能为空', trigger: 'change' }],
    userName: [
      { required: true, message: '登录账号不能为空', trigger: 'blur' },
      { min: 2, max: 20, message: '登录账号长度必须介于 2 和 20 之间', trigger: 'blur' }
    ],
    password: [
      { required: true, message: '初始密码不能为空', trigger: 'blur' },
      { min: 5, max: 20, message: '密码长度必须介于 5 和 20 之间', trigger: 'blur' },
      { pattern: /^[^<>"'|\\]+$/, message: '密码不能包含非法字符', trigger: 'blur' }
    ],
    phonenumber: [{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }]
  }
})
const { form, queryParams, rules } = toRefs(data)

function findBrigade(nodes) {
  for (const node of nodes || []) {
    if (node.id === BRIGADE_DEPT_ID) return node
    const found = findBrigade(node.children)
    if (found) return found
  }
}

function filterEnabled(nodes) {
  return (nodes || []).filter(node => !node.disabled).map(node => ({
    ...node,
    children: filterEnabled(node.children)
  }))
}

function getDeptTree() {
  deptTreeSelect().then(response => {
    const brigade = findBrigade(response.data)
    deptOptions.value = brigade ? [brigade] : []
    enabledDeptOptions.value = filterEnabled(JSON.parse(JSON.stringify(deptOptions.value)))
    nextTick(() => deptTreeRef.value?.setCurrentKey(BRIGADE_DEPT_ID))
  })
}

function getList() {
  loading.value = true
  listUser(queryParams.value).then(response => {
    userList.value = response.rows
    total.value = response.total
  }).finally(() => { loading.value = false })
}

function roleLabel(role) {
  if (role.roleId === 1) return '大队管理员'
  return role.roleName
}

function handleNodeClick(node) {
  queryParams.value.deptId = node.id
  handleQuery()
}

function handleQuery() {
  queryParams.value.pageNum = 1
  getList()
}

function resetQuery() {
  proxy.resetForm('queryRef')
  queryParams.value.deptId = BRIGADE_DEPT_ID
  deptTreeRef.value?.setCurrentKey(BRIGADE_DEPT_ID)
  handleQuery()
}

function reset() {
  form.value = {
    userId: undefined,
    deptId: undefined,
    userName: undefined,
    nickName: undefined,
    password: undefined,
    phonenumber: undefined,
    status: '0',
    remark: undefined,
    roleId: undefined,
    roleIds: [],
    postIds: []
  }
  proxy.resetForm('userRef')
}

function setOptions(response) {
  roleOptions.value = response.roles.filter(role => PLATFORM_ROLE_IDS.includes(role.roleId) && role.status === '0')
}

function handleAdd() {
  reset()
  getUser().then(response => {
    setOptions(response)
    form.value.password = initPassword.value
    form.value.deptId = BRIGADE_DEPT_ID
    open.value = true
    title.value = '新增平台账号'
  })
}

function handleUpdate(row) {
  reset()
  getUser(row.userId).then(response => {
    setOptions(response)
    form.value = {
      ...response.data,
      password: undefined,
      postIds: [],
      roleIds: response.roleIds,
      roleId: response.roleIds.find(id => PLATFORM_ROLE_IDS.includes(id))
    }
    open.value = true
    title.value = '修改平台账号'
  })
}

function submitForm() {
  proxy.$refs.userRef.validate(valid => {
    if (!valid) return
    const payload = { ...form.value, roleIds: [form.value.roleId], postIds: [], email: '', sex: '0' }
    const request = payload.userId ? updateUser(payload) : addUser(payload)
    request.then(() => {
      proxy.$modal.msgSuccess(payload.userId ? '修改成功' : '新增成功')
      open.value = false
      getList()
    })
  })
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.userId)
}

function handleDelete(row) {
  const userIds = row?.userId || ids.value
  const subject = row?.nickName || `选中的 ${ids.value.length} 个账号`
  proxy.$modal.confirm(`是否删除“${subject}”？`).then(() => delUser(userIds)).then(() => {
    proxy.$modal.msgSuccess('删除成功')
    getList()
  }).catch(() => {})
}

function handleStatusChange(row) {
  const action = row.status === '0' ? '启用' : '停用'
  proxy.$modal.confirm(`是否${action}“${row.nickName}”？`).then(() => changeUserStatus(row.userId, row.status)).then(() => {
    proxy.$modal.msgSuccess(`${action}成功`)
  }).catch(() => { row.status = row.status === '0' ? '1' : '0' })
}

function handleResetPwd(row) {
  proxy.$prompt(`请输入“${row.nickName}”的新密码`, '重置密码', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    closeOnClickModal: false,
    inputPattern: /^(?=.{5,20}$)[^<>"'|\\]+$/,
    inputErrorMessage: '密码长度为 5 至 20 位，且不能包含非法字符'
  }).then(({ value }) => resetUserPwd(row.userId, value)).then(() => {
    proxy.$modal.msgSuccess('密码重置成功')
  }).catch(() => {})
}

onMounted(() => {
  getDeptTree()
  getList()
  proxy.getConfigKey('sys.user.initPassword').then(response => { initPassword.value = response.msg })
})
</script>

<style scoped>
.user-management { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 20px; }
.org-panel { min-height: calc(100vh - 124px); padding-right: 18px; border-right: 1px solid var(--el-border-color-light); }
.panel-title { margin-bottom: 14px; color: var(--el-text-color-primary); font-size: 15px; font-weight: 600; }
.user-content { min-width: 0; }
.role-tag { margin-right: 4px; }
.w-full { width: 100%; }
@media (max-width: 768px) {
  .user-management { grid-template-columns: 1fr; }
  .org-panel { min-height: auto; padding: 0 0 14px; border-right: 0; border-bottom: 1px solid var(--el-border-color-light); }
}
</style>
