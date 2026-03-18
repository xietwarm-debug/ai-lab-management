<template>
  <div class="page-container duty-page">
    <!-- 顶部 Hero 区 (带入场动画，应急专属红色调) -->
    <section class="hero-card overview-section is-danger-theme">
      <div class="hero-content">
        <div class="hero-copy">
          <span class="eyebrow">On Call</span>
          <h1 class="page-title">值班与应急处置</h1>
          <p class="page-desc">统一管理值班表、实验室事故上报、应急联系人和处置闭环，适配实验室日常值守场景。</p>
        </div>
        <div class="hero-actions">
          <el-button type="danger" plain :loading="loading" @click="loadAll" :icon="RefreshRight" class="hover-lift">
            刷新全局状态
          </el-button>
        </div>
      </div>
      <div class="hero-decoration"></div>
    </section>

    <!-- 核心操作区 (Tabs面板) -->
    <section class="panel-card main-tabs-panel panel-fade-in">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <!-- 1. 值班表 Tab -->
        <el-tab-pane name="duty">
          <template #label>
            <span class="tab-label-custom"><el-icon><Calendar /></el-icon> 值班表</span>
          </template>
          
          <div class="tab-grid mt-4">
            <!-- 左侧：表单 -->
            <article class="sub-card panel-fade-in">
              <div class="sub-head">
                <div class="head-left">
                  <h3>新增 / 编辑值班</h3>
                  <span>支持白班、晚班、周末等班次</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="日期">
                      <el-date-picker v-model="dutyForm.dutyDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="班次">
                      <el-input v-model="dutyForm.shiftName" placeholder="如：白班 / 晚班" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="值班人">
                      <el-input v-model="dutyForm.assigneeName" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="值班电话">
                      <el-input v-model="dutyForm.assigneePhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="备岗人">
                      <el-input v-model="dutyForm.backupName" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="备岗电话">
                      <el-input v-model="dutyForm.backupPhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="dutyForm.status" style="width: 100%">
                        <el-option label="待值班" value="scheduled" />
                        <el-option label="值班中" value="on_duty" />
                        <el-option label="已完成" value="completed" />
                        <el-option label="已关闭" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="备注">
                      <el-input v-model="dutyForm.note" placeholder="选填，输入特殊交接事项..." />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetDutyForm">清空</el-button>
                <el-button type="primary" :loading="savingDuty" @click="saveDuty" class="hover-lift">保存值班</el-button>
              </div>
            </article>

            <!-- 右侧：列表 -->
            <article class="sub-card table-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>值班列表</h3>
                  <span class="count-badge">{{ dutyRows.length }} 条</span>
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="dutyRows" style="width: 100%">
                  <el-table-column prop="dutyDate" label="日期" min-width="110" />
                  <el-table-column prop="shiftName" label="班次" min-width="90" />
                  <el-table-column prop="assigneeName" label="值班人" min-width="100" />
                  <el-table-column prop="status" label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getStatusType(row.status)" effect="light" class="custom-tag">
                        {{ getStatusLabel(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="180" fixed="right" align="right">
                    <template #default="{ row }">
                      <div class="row-actions">
                        <el-button link type="primary" @click="editDuty(row)">编辑</el-button>
                        <el-button link type="warning" @click="quickDutyStatus(row, 'on_duty')">值班</el-button>
                        <el-button link type="success" @click="quickDutyStatus(row, 'completed')">完成</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <!-- 2. 事故处置 Tab -->
        <el-tab-pane name="incident">
          <template #label>
            <span class="tab-label-custom"><el-icon><Warning /></el-icon> 事故处置</span>
          </template>
          
          <div class="tab-grid mt-4">
            <article class="sub-card panel-fade-in">
              <div class="sub-head">
                <div class="head-left">
                  <h3 class="danger-border">事故上报</h3>
                  <span>支持实验室事故、异常事件和处置闭环</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="实验室">
                      <el-select v-model="incidentForm.labId" style="width: 100%" clearable @change="syncIncidentLabName">
                        <el-option v-for="lab in labOptions" :key="lab.labId || lab.id" :label="lab.labName || lab.name" :value="lab.labId || lab.id" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="事故等级">
                      <el-select v-model="incidentForm.incidentLevel" style="width: 100%">
                        <el-option label="低 (Low)" value="low" />
                        <el-option label="中 (Medium)" value="medium" />
                        <el-option label="高 (High)" value="high" />
                        <el-option label="严重 (Critical)" value="critical" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="标题">
                      <el-input v-model="incidentForm.title" placeholder="简述事故核心现象" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="incidentForm.status" style="width: 100%">
                        <el-option label="已上报" value="reported" />
                        <el-option label="处理中" value="processing" />
                        <el-option label="已闭环" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="上报人">
                      <el-input v-model="incidentForm.reporterName" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="联系电话">
                      <el-input v-model="incidentForm.reporterPhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="事件描述">
                      <el-input v-model="incidentForm.description" type="textarea" :rows="3" placeholder="详细描述发生时间、地点、涉事设备及人员..." />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="处置记录">
                      <el-input v-model="incidentForm.disposalNote" type="textarea" :rows="3" placeholder="填写后续跟进、处理方案及结果..." />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetIncidentForm">清空</el-button>
                <el-button type="danger" :loading="savingIncident" @click="saveIncidentRecord" class="hover-lift">保存事故记录</el-button>
              </div>
            </article>

            <article class="sub-card table-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>事故列表</h3>
                  <span class="count-badge">{{ incidentRows.length }} 条</span>
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="incidentRows" style="width: 100%">
                  <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="labName" label="实验室" min-width="120" show-overflow-tooltip />
                  <el-table-column prop="incidentLevel" label="等级" width="90">
                     <template #default="{ row }">
                      <span class="severity-dot" :class="`is-${row.incidentLevel}`"></span>
                      {{ getLevelLabel(row.incidentLevel) }}
                     </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="100">
                     <template #default="{ row }">
                      <el-tag size="small" :type="row.status === 'closed' ? 'info' : (row.status === 'reported' ? 'danger' : 'warning')" class="custom-tag">
                        {{ row.status === 'closed' ? '已闭环' : (row.status === 'processing' ? '处理中' : '已上报') }}
                      </el-tag>
                     </template>
                  </el-table-column>
                  <el-table-column label="操作" width="160" fixed="right" align="right">
                    <template #default="{ row }">
                      <div class="row-actions">
                        <el-button link type="primary" @click="editIncident(row)">编辑</el-button>
                        <el-button link type="warning" @click="quickIncidentStatus(row, 'processing')" v-if="row.status !== 'processing' && row.status !== 'closed'">处理</el-button>
                        <el-button link type="success" @click="quickIncidentStatus(row, 'closed')" v-if="row.status !== 'closed'">闭环</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <!-- 3. 应急联系人 Tab -->
        <el-tab-pane name="contacts">
          <template #label>
            <span class="tab-label-custom"><el-icon><Phone /></el-icon> 应急联系人</span>
          </template>
          
          <div class="tab-grid mt-4">
            <article class="sub-card panel-fade-in">
              <div class="sub-head">
                <div class="head-left">
                  <h3>联系人维护</h3>
                  <span>值班电话、网络中心、保卫处、后勤等统一维护</span>
                </div>
              </div>
              <el-form label-position="top" class="custom-form">
                <el-row :gutter="20">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="姓名 / 部门">
                      <el-input v-model="contactForm.name" placeholder="如：保卫处报警中心" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="岗位 / 职责">
                      <el-input v-model="contactForm.roleName" placeholder="如：校区安保" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="电话">
                      <el-input v-model="contactForm.phone" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="显示优先级">
                      <el-input-number v-model="contactForm.priorityNo" :min="1" :max="999" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="状态">
                      <el-select v-model="contactForm.status" style="width: 100%">
                        <el-option label="启用" value="active" />
                        <el-option label="停用" value="inactive" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="补充说明">
                      <el-input v-model="contactForm.description" placeholder="支持24小时接听等说明..." />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetContactForm">清空</el-button>
                <el-button type="primary" :loading="savingContact" @click="saveContactRecord" class="hover-lift">保存联系人</el-button>
              </div>
            </article>

            <article class="sub-card table-card panel-fade-in" style="animation-delay: 0.1s;">
              <div class="sub-head">
                <div class="head-left">
                  <h3>联系人名录</h3>
                  <span class="count-badge">{{ contactRows.length }} 条</span>
                </div>
              </div>
              <div class="table-wrapper">
                <el-table :data="contactRows" style="width: 100%">
                  <el-table-column prop="priorityNo" label="优先级" width="80" align="center" />
                  <el-table-column prop="name" label="姓名/部门" min-width="130" />
                  <el-table-column prop="phone" label="电话" min-width="130">
                    <template #default="{ row }">
                      <strong class="text-primary">{{ row.phone }}</strong>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" label="状态" width="90">
                     <template #default="{ row }">
                      <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'" class="custom-tag">
                        {{ row.status === 'active' ? '启用' : '停用' }}
                      </el-tag>
                     </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" fixed="right" align="right">
                    <template #default="{ row }">
                      <div class="row-actions">
                        <el-button link type="primary" @click="editContact(row)">编辑</el-button>
                        <el-button link type="danger" @click="deleteContactRecord(row)">删除</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Calendar, Warning, Phone } from '@element-plus/icons-vue'

// 假设的 API
import { getLabs } from '@/api/labs'
import {
  deleteEmergencyContact,
  getDutyRoster,
  getEmergencyContacts,
  getIncidents,
  saveDutyRoster,
  saveEmergencyContact,
  saveIncident,
  updateDutyRosterStatus,
  updateIncidentStatus
} from '@/api/duty'

const activeTab = ref('duty')
const loading = ref(false)
const savingDuty = ref(false)
const savingIncident = ref(false)
const savingContact = ref(false)

const dutyRows = ref([])
const incidentRows = ref([])
const contactRows = ref([])
const labOptions = ref([])

const dutyForm = reactive({
  id: null, dutyDate: '', shiftName: '', assigneeName: '', assigneePhone: '', backupName: '', backupPhone: '', status: 'scheduled', note: ''
})

const incidentForm = reactive({
  id: null, labId: null, labName: '', title: '', incidentLevel: 'medium', status: 'reported', reporterName: '', reporterPhone: '', emergencyContactName: '', description: '', disposalNote: ''
})

const contactForm = reactive({
  id: null, name: '', roleName: '', phone: '', priorityNo: 10, status: 'active', description: ''
})

// --- UI 辅助函数 ---
const getStatusType = (status) => {
  const map = { scheduled: 'info', on_duty: 'primary', completed: 'success', closed: 'info' }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = { scheduled: '待值班', on_duty: '值班中', completed: '已完成', closed: '已关闭' }
  return map[status] || status
}

const getLevelLabel = (level) => {
  const map = { low: '低', medium: '中', high: '高', critical: '严重' }
  return map[level] || level
}

// --- 业务逻辑保持原样 ---
function resetDutyForm() {
  dutyForm.id = null; dutyForm.dutyDate = ''; dutyForm.shiftName = ''; dutyForm.assigneeName = ''; dutyForm.assigneePhone = ''; dutyForm.backupName = ''; dutyForm.backupPhone = ''; dutyForm.status = 'scheduled'; dutyForm.note = ''
}

function resetIncidentForm() {
  incidentForm.id = null; incidentForm.labId = null; incidentForm.labName = ''; incidentForm.title = ''; incidentForm.incidentLevel = 'medium'; incidentForm.status = 'reported'; incidentForm.reporterName = ''; incidentForm.reporterPhone = ''; incidentForm.emergencyContactName = ''; incidentForm.description = ''; incidentForm.disposalNote = ''
}

function resetContactForm() {
  contactForm.id = null; contactForm.name = ''; contactForm.roleName = ''; contactForm.phone = ''; contactForm.priorityNo = 10; contactForm.status = 'active'; contactForm.description = ''
}

function syncIncidentLabName() {
  const matched = labOptions.value.find((item) => Number(item.labId || item.id) === Number(incidentForm.labId || 0))
  incidentForm.labName = matched ? String(matched.labName || matched.name || '') : ''
}

async function loadAll() {
  loading.value = true
  try {
    const [labRes, dutyRes, incidentRes, contactRes] = await Promise.all([
      getLabs({ pageSize: 500 }).catch(() => ({ data: { data: [] } })),
      getDutyRoster({}).catch(() => ({ data: { data: [] } })),
      getIncidents({}).catch(() => ({ data: { data: [] } })),
      getEmergencyContacts({}).catch(() => ({ data: { data: [] } }))
    ])
    labOptions.value = Array.isArray(labRes.data?.data) ? labRes.data.data : []
    dutyRows.value = Array.isArray(dutyRes.data?.data) ? dutyRes.data.data : []
    incidentRows.value = Array.isArray(incidentRes.data?.data) ? incidentRes.data.data : []
    contactRows.value = Array.isArray(contactRes.data?.data) ? contactRes.data.data : []
  } finally {
    loading.value = false
  }
}

async function saveDuty() {
  if (!dutyForm.dutyDate || !dutyForm.shiftName || !dutyForm.assigneeName) {
    ElMessage.warning('请至少填写日期、班次和值班人')
    return
  }
  savingDuty.value = true
  try {
    await saveDutyRoster({ ...dutyForm })
    ElMessage.success('值班信息已保存')
    resetDutyForm()
    await loadAll()
  } catch (e) {} finally { savingDuty.value = false }
}

function editDuty(row) { Object.assign(dutyForm, { ...row }) }

async function quickDutyStatus(row, status) {
  try {
    await updateDutyRosterStatus(row.id, { status, note: row.note || '' })
    ElMessage.success('值班状态已更新')
    await loadAll()
  } catch (e) {}
}

async function saveIncidentRecord() {
  if (!incidentForm.title) {
    ElMessage.warning('请填写事故标题')
    return
  }
  savingIncident.value = true
  try {
    await saveIncident({ ...incidentForm })
    ElMessage.success('事故记录已保存')
    resetIncidentForm()
    await loadAll()
  } catch (e) {} finally { savingIncident.value = false }
}

function editIncident(row) { Object.assign(incidentForm, { ...row }) }

async function quickIncidentStatus(row, status) {
  const disposalNote = status === 'closed'
    ? `${row.disposalNote || ''}\n${new Date().toLocaleString()} 已闭环`.trim()
    : row.disposalNote || ''
  try {
    await updateIncidentStatus(row.id, { status, disposalNote })
    ElMessage.success('事故状态已更新')
    await loadAll()
  } catch (e) {}
}

async function saveContactRecord() {
  if (!contactForm.name || !contactForm.phone) {
    ElMessage.warning('请填写联系人姓名和电话')
    return
  }
  savingContact.value = true
  try {
    await saveEmergencyContact({ ...contactForm })
    ElMessage.success('联系人已保存')
    resetContactForm()
    await loadAll()
  } catch (e) {} finally { savingContact.value = false }
}

function editContact(row) { Object.assign(contactForm, { ...row }) }

async function deleteContactRecord(row) {
  try {
    await ElMessageBox.confirm(`确认删除联系人 ${row.name} 吗？`, '删除联系人', { type: 'warning' })
    await deleteEmergencyContact(row.id)
    ElMessage.success('联系人已删除')
    await loadAll()
  } catch (e) { /* 用户取消或失败 */ }
}

onMounted(() => { loadAll() })
</script>

<style scoped lang="scss">
// 统一的学术极简设计变量
$bg-color: #f8fafc;
$card-bg: #ffffff;
$text-main: #0f172a;
$text-regular: #475569;
$text-light: #94a3b8;
$border-color: #e2e8f0;
$primary: #3b82f6;
$danger: #ef4444;
$danger-light: #fef2f2;
$warning: #f59e0b;
$success: #10b981;
$radius-lg: 16px;
$radius-md: 12px;
$shadow-soft: 0 10px 30px rgba(0, 0, 0, 0.03);
$shadow-hover: 0 15px 35px rgba(59, 130, 246, 0.06);
$shadow-danger-hover: 0 15px 35px rgba(239, 68, 68, 0.08);

// --- 入场动画 Keyframes ---
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-container {
  padding: 32px;
  background-color: $bg-color;
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// 工具类
.mt-4 { margin-top: 16px; }
.text-primary { color: $primary; }
.hover-lift { transition: transform 0.2s ease; &:hover { transform: translateY(-1px); } }
.panel-fade-in {
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  &:nth-child(n+1) { animation-delay: 0.1s; }
  &:nth-child(n+2) { animation-delay: 0.15s; }
}

/* --- Hero 区域 (应急专属红色主题) --- */
.hero-card {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 32px;
  background: #ffffff;
  border-radius: $radius-lg;
  box-shadow: $shadow-soft;
  overflow: hidden;
  animation: fadeSlideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;

  &.is-danger-theme {
    background: radial-gradient(circle at top right, rgba(239, 68, 68, 0.08), transparent 60%),
                linear-gradient(135deg, #ffffff 0%, #fff5f5 100%);
    border: 1px solid rgba(239, 68, 68, 0.1);
  }

  .hero-decoration {
    position: absolute; right: 0; top: 0; width: 300px; height: 100%;
    pointer-events: none;
    background-image: radial-gradient(#ef4444 1px, transparent 1px);
    background-size: 20px 20px;
    opacity: 0.05;
    mask-image: linear-gradient(to left, white, transparent);
  }

  .hero-content {
    position: relative; z-index: 1; display: flex; justify-content: space-between;
    align-items: flex-end; width: 100%; flex-wrap: wrap; gap: 24px;
  }

  .eyebrow {
    display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px;
    background: $danger-light; color: #b91c1c; font-size: 13px; font-weight: 700;
    margin-bottom: 12px; letter-spacing: 0.05em;
  }

  .page-title { font-size: 28px; font-weight: 700; color: $text-main; margin: 0 0 12px 0; }
  .page-desc { color: $text-regular; font-size: 14px; margin: 0; max-width: 600px; line-height: 1.6; }
}

/* --- 面板基础与 Tabs --- */
.panel-card {
  background: $card-bg; border-radius: $radius-lg; padding: 24px;
  box-shadow: $shadow-soft; border: 1px solid transparent;
}

.main-tabs-panel { padding-top: 16px; }

:deep(.custom-tabs) {
  .el-tabs__nav-wrap::after { height: 1px; background-color: $border-color; }
  .el-tabs__active-bar { background-color: $primary; height: 3px; border-radius: 3px 3px 0 0; }
  .el-tabs__item {
    font-size: 16px; color: $text-regular; font-weight: 500; padding: 0 24px; transition: all 0.3s;
    &:hover { color: $primary; }
    &.is-active { color: $text-main; font-weight: 600; }
  }
  .tab-label-custom { display: flex; align-items: center; gap: 8px; }
}

/* --- 内部网格布局 --- */
.tab-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.8fr); // 左侧表单较窄，右侧表格较宽
  gap: 24px;
}

/* --- 子卡片 (表单区与表格区) --- */
.sub-card {
  background: #f8fafc; border-radius: $radius-md; padding: 24px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  transition: all 0.3s ease;
  display: flex; flex-direction: column;

  &:hover { box-shadow: $shadow-hover; background: #ffffff; border-color: rgba(59, 130, 246, 0.1); }
  &.table-card { padding: 0; background: #ffffff; overflow: hidden; }
}

.sub-head {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;
  
  .head-left {
    h3 { 
      font-size: 16px; font-weight: 600; color: $text-main; margin: 0 0 6px 0;
      border-left: 4px solid $primary; padding-left: 10px;
      &.danger-border { border-left-color: $danger; }
    }
    span { color: $text-light; font-size: 13px; padding-left: 14px; display: block;}
    .count-badge { display: inline-block; background: #f1f5f9; padding: 2px 10px; border-radius: 12px; margin-left: 14px; padding-left: 10px; }
  }
}

.table-card .sub-head { padding: 20px 24px 0 24px; margin-bottom: 16px; }

.action-row { display: flex; justify-content: flex-end; gap: 12px; margin-top: auto; padding-top: 24px; }

/* --- 表单样式优化 (Academic Minimalist) --- */
:deep(.custom-form) {
  .el-form-item__label { font-weight: 500; color: $text-regular; padding-bottom: 4px; }
  .el-input__wrapper, .el-select__wrapper {
    background-color: #ffffff; border-radius: 8px; box-shadow: 0 0 0 1px $border-color inset; transition: all 0.2s;
    &:hover { box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.5) inset; }
    &.is-focus { box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) inset, 0 0 0 1px $primary inset !important; }
  }
  .el-textarea__inner {
    border-radius: 8px; box-shadow: 0 0 0 1px $border-color inset; padding: 12px; font-family: inherit;
    &:focus { box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) inset, 0 0 0 1px $primary inset; }
  }
}

/* --- 表格样式优化 (去除边框，增加呼吸感) --- */
.table-wrapper {
  padding: 0 24px 24px 24px;
}

:deep(.el-table) {
  --el-table-border-color: #f1f5f9;
  --el-table-header-bg-color: #f8fafc;
  --el-table-header-text-color: #64748b;
  border-radius: 8px;
  
  th.el-table__cell { font-weight: 600; font-size: 13px; }
  td.el-table__cell { padding: 12px 0; color: $text-main; }
  
  &::before, .el-table__inner-wrapper::before { display: none; } // 移除最底部边框
  .el-table__row { transition: background-color 0.2s; }
  .el-table__row:hover > td.el-table__cell { background-color: #f8fafc !important; }
}

.row-actions { display: flex; gap: 4px; justify-content: flex-end; }

/* --- 状态标签与圆点 --- */
:deep(.custom-tag) { border-radius: 6px; font-weight: 500; border: none; }

.severity-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;
  &.is-low { background-color: $success; }
  &.is-medium { background-color: $warning; }
  &.is-high { background-color: #f97316; } // 橙红色
  &.is-critical { background-color: $danger; box-shadow: 0 0 0 3px $danger-light; }
}

/* --- 响应式 --- */
@media (max-width: 1200px) {
  .tab-grid { grid-template-columns: 1fr; }
  .table-card { min-height: 400px; }
}

@media (max-width: 768px) {
  .hero-content, .sub-head { flex-direction: column; align-items: flex-start; }
  .page-container { padding: 16px; }
}
</style>