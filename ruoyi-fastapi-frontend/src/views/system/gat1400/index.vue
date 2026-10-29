<template>
  <div class="app-container">
    <el-card class="mb8" shadow="never">
      <template #header>
        <div class="card-header">
          <span>对接状态</span>
          <div>
            <el-button v-hasPermi="['gat1400:connect:operate']" icon="Setting" plain size="small" type="primary" @click="openConfig">对接配置</el-button>
            <el-button v-hasPermi="['gat1400:connect:query']" icon="Refresh" plain size="small" @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="对接开关">
          <el-tag :type="status.enabled ? 'success' : 'info'">{{ status.enabled ? '已启用' : '未启用' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册状态">
          <el-tag :type="statusType(status.registerStatus)">{{ statusName(status.registerStatus) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="保活间隔">{{ status.keepaliveInterval }}s</el-descriptions-item>
        <el-descriptions-item label="平台地址">{{ status.platformAddr || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备ID">{{ status.deviceId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="连续失败次数">{{ status.failCount }}</el-descriptions-item>
        <el-descriptions-item label="最近注册时间">{{ status.lastRegisterTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近保活时间">{{ status.lastKeepaliveTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="保活累计次数">{{ status.keepaliveCount }}</el-descriptions-item>
        <el-descriptions-item label="下次重试时间">{{ status.nextRetryAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2">
          <el-text v-if="status.errorMessage" type="danger">{{ status.errorMessage }}</el-text>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
      <div class="mb8 mt8">
        <el-button v-hasPermi="['gat1400:connect:operate']" icon="Link" type="primary" :loading="operating" @click="handleRegister">手动注册</el-button>
        <el-button v-hasPermi="['gat1400:connect:operate']" icon="RefreshRight" plain type="success" :loading="operating" @click="handleKeepalive">手动保活</el-button>
        <el-button v-hasPermi="['gat1400:connect:operate']" icon="CircleClose" plain type="danger" :loading="operating" @click="handleUnregister">注销对接</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>订阅管理</span>
          <el-button v-hasPermi="['gat1400:connect:operate']" icon="Plus" plain size="small" type="primary" @click="handleCreateSubscribe">创建订阅</el-button>
        </div>
      </template>
      <el-table v-loading="subscribeLoading" :data="subscribeList">
        <el-table-column label="订阅ID" min-width="260" prop="subscribeId" show-overflow-tooltip />
        <el-table-column label="标题" min-width="120" prop="title" />
        <el-table-column label="订阅类别" min-width="100" prop="subscribeDetail" />
        <el-table-column label="资源ID" min-width="190" prop="resourceUri" show-overflow-tooltip />
        <el-table-column label="开始时间" min-width="150" prop="beginTime" />
        <el-table-column label="结束时间" min-width="150" prop="endTime" />
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.subscribeStatus === '0' ? 'success' : 'info'">{{ scope.row.subscribeStatus === '0' ? '订阅中' : '已取消' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="100">
          <template #default="scope">
            <el-button v-if="scope.row.subscribeStatus === '0'" v-hasPermi="['gat1400:connect:operate']" link type="danger" @click="handleCancelSubscribe(scope.row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 对接配置弹窗 -->
    <el-dialog v-model="configVisible" title="对接配置" width="640px" append-to-body>
      <el-form ref="configRef" :model="configForm" :rules="configRules" label-width="140px">
        <el-divider content-position="left">基础连接</el-divider>
        <el-form-item label="启用对接" prop="enabled">
          <el-switch v-model="configForm.enabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="平台地址" prop="platformAddr">
          <el-input v-model="configForm.platformAddr" placeholder="http://ip:port" />
        </el-form-item>
        <el-form-item label="设备ID" prop="deviceId">
          <el-input v-model="configForm.deviceId" maxlength="20" placeholder="20位设备ID，可自定义" />
        </el-form-item>
        <el-form-item label="认证账号" prop="username">
          <el-input v-model="configForm.username" placeholder="大华平台分配的摘要认证账号" />
        </el-form-item>
        <el-form-item label="认证密码" prop="password">
          <el-input v-model="configForm.password" :placeholder="configForm.passwordSet ? '已配置（留空表示不修改）' : '大华平台分配的认证密码'" show-password />
        </el-form-item>
        <el-form-item label="保活间隔(秒)" prop="keepaliveInterval">
          <el-input-number v-model="configForm.keepaliveInterval" :min="10" :max="300" />
        </el-form-item>
        <el-divider content-position="left">订阅</el-divider>
        <el-form-item label="订阅类别" prop="subscribeDetail">
          <el-input v-model="configForm.subscribeDetail" placeholder="13=过车记录，多个用逗号分隔" />
        </el-form-item>
        <el-form-item label="订阅资源ID" prop="subscribeResourceUri">
          <el-input v-model="configForm.subscribeResourceUri" placeholder="大华平台下发的资源ID" />
        </el-form-item>
        <el-form-item label="申请人" prop="applicantName">
          <el-input v-model="configForm.applicantName" />
        </el-form-item>
        <el-form-item label="申请单位" prop="applicantOrg">
          <el-input v-model="configForm.applicantOrg" />
        </el-form-item>
        <el-form-item label="订阅有效期(天)" prop="subscribeDays">
          <el-input-number v-model="configForm.subscribeDays" :min="1" :max="365" />
        </el-form-item>
        <el-form-item label="回调地址" prop="receiveAddr">
          <el-input v-model="configForm.receiveAddr" placeholder="http://本机IP/VIID/SubscribeNotifications" />
        </el-form-item>
        <el-divider content-position="left">安全</el-divider>
        <el-form-item label="通知IP白名单" prop="notifyAllowedIps">
          <el-input v-model="configForm.notifyAllowedIps" placeholder="逗号分隔，留空不限制（建议填大华平台IP）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configVisible = false">取消</el-button>
        <el-button type="primary" :loading="configSaving" @click="handleSaveConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="TruckGat1400">
import { cancelSubscribe, createSubscribe, gat1400Keepalive, gat1400Register, gat1400Unregister, getGat1400Config, getGat1400Status, listSubscribe, saveGat1400Config } from '@/api/system/gat1400'

const { proxy } = getCurrentInstance()
const status = ref({})
const configVisible = ref(false)
const configSaving = ref(false)
const configForm = ref({})
const configRules = {
  platformAddr: [{ required: true, message: '平台地址不能为空', trigger: 'blur' }],
  deviceId: [{ required: true, message: '设备ID不能为空', trigger: 'blur' }],
  username: [{ required: true, message: '认证账号不能为空', trigger: 'blur' }]
}
const subscribeList = ref([])
const subscribeLoading = ref(false)
const operating = ref(false)

const STATUS_NAMES = { unregistered: '未注册', registering: '注册中', online: '在线', offline: '离线' }
const STATUS_TYPES = { unregistered: 'info', registering: 'warning', online: 'success', offline: 'danger' }
function statusName(value) { return STATUS_NAMES[value] || value }
function statusType(value) { return STATUS_TYPES[value] || 'info' }

function loadStatus() {
  getGat1400Status().then(response => { status.value = response.data || {} })
}
function loadSubscribes() {
  subscribeLoading.value = true
  listSubscribe().then(response => { subscribeList.value = response.data || [] }).finally(() => { subscribeLoading.value = false })
}
function loadAll() { loadStatus(); loadSubscribes() }

function run(action, successMsg) {
  operating.value = true
  action().then(response => {
    proxy.$modal.msgSuccess(response.msg || successMsg)
    loadAll()
  }).finally(() => { operating.value = false })
}
function handleRegister() { run(gat1400Register, '注册完成') }
function handleKeepalive() { run(gat1400Keepalive, '保活完成') }
function handleUnregister() {
  proxy.$modal.confirm('注销后平台将停止推送过车数据，是否继续？').then(() => {
    run(gat1400Unregister, '注销完成')
  }).catch(() => {})
}
function handleCreateSubscribe() {
  proxy.$modal.confirm('将向大华平台创建订阅（类别按配置），是否继续？').then(() => {
    run(createSubscribe, '订阅创建完成')
  }).catch(() => {})
}
function handleCancelSubscribe(row) {
  proxy.$modal.confirm(`确认取消订阅 ${row.subscribeId}？取消后平台将停止推送该订阅数据。`).then(() => {
    run(() => cancelSubscribe(row.subscribeId), '订阅已取消')
  }).catch(() => {})
}

function openConfig() {
  getGat1400Config().then(response => {
    configForm.value = response.data || {}
    configVisible.value = true
  })
}
function handleSaveConfig() {
  proxy.$refs.configRef.validate(valid => {
    if (!valid) return
    configSaving.value = true
    saveGat1400Config(configForm.value).then(response => {
      proxy.$modal.msgSuccess(response.msg || '配置保存成功')
      configVisible.value = false
      loadAll()
    }).finally(() => { configSaving.value = false })
  })
}

loadAll()
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.mt8 { margin-top: 8px; }
</style>
