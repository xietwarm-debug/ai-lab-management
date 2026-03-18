<template>
  <div class="duty-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">On Call</span>
        <h2>值班与应急处置</h2>
        <p>统一管理值班表、实验室事故上报、应急联系人和处置闭环，适配实验室日常值守场景。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </section>

    <section class="panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="值班表" name="duty">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>新增 / 编辑值班</h3>
                <span>支持白班、晚班、周末等班次</span>
              </div>
              <el-form label-position="top">
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="日期">
                      <el-date-picker v-model="dutyForm.dutyDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="班次">
                      <el-input v-model="dutyForm.shiftName" placeholder="如：白班 / 晚班" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="值班人">
                      <el-input v-model="dutyForm.assigneeName" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="值班电话">
                      <el-input v-model="dutyForm.assigneePhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="备岗人">
                      <el-input v-model="dutyForm.backupName" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="备岗电话">
                      <el-input v-model="dutyForm.backupPhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="状态">
                      <el-select v-model="dutyForm.status" style="width: 100%">
                        <el-option label="待值班" value="scheduled" />
                        <el-option label="值班中" value="on_duty" />
                        <el-option label="已完成" value="completed" />
                        <el-option label="已关闭" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="备注">
                      <el-input v-model="dutyForm.note" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetDutyForm">清空</el-button>
                <el-button type="primary" :loading="savingDuty" @click="saveDuty">保存值班</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>值班列表</h3>
                <span>{{ dutyRows.length }} 条</span>
              </div>
              <el-table :data="dutyRows" stripe>
                <el-table-column prop="dutyDate" label="日期" min-width="120" />
                <el-table-column prop="shiftName" label="班次" min-width="100" />
                <el-table-column prop="assigneeName" label="值班人" min-width="120" />
                <el-table-column prop="assigneePhone" label="电话" min-width="140" />
                <el-table-column prop="status" label="状态" width="110" />
                <el-table-column label="操作" min-width="220">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="editDuty(row)">编辑</el-button>
                    <el-button text @click="quickDutyStatus(row, 'on_duty')">值班中</el-button>
                    <el-button text type="success" @click="quickDutyStatus(row, 'completed')">完成</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="事故处置" name="incident">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>事故上报</h3>
                <span>支持实验室事故、异常事件和处置闭环</span>
              </div>
              <el-form label-position="top">
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="实验室">
                      <el-select v-model="incidentForm.labId" style="width: 100%" clearable @change="syncIncidentLabName">
                        <el-option v-for="lab in labOptions" :key="lab.labId || lab.id" :label="lab.labName || lab.name" :value="lab.labId || lab.id" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="事故等级">
                      <el-select v-model="incidentForm.incidentLevel" style="width: 100%">
                        <el-option label="低" value="low" />
                        <el-option label="中" value="medium" />
                        <el-option label="高" value="high" />
                        <el-option label="严重" value="critical" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="标题">
                      <el-input v-model="incidentForm.title" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="状态">
                      <el-select v-model="incidentForm.status" style="width: 100%">
                        <el-option label="已上报" value="reported" />
                        <el-option label="处理中" value="processing" />
                        <el-option label="已闭环" value="closed" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="上报人">
                      <el-input v-model="incidentForm.reporterName" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="联系电话">
                      <el-input v-model="incidentForm.reporterPhone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="事件描述">
                      <el-input v-model="incidentForm.description" type="textarea" :rows="4" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item label="处置记录">
                      <el-input v-model="incidentForm.disposalNote" type="textarea" :rows="4" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetIncidentForm">清空</el-button>
                <el-button type="primary" :loading="savingIncident" @click="saveIncidentRecord">保存事故</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>事故列表</h3>
                <span>{{ incidentRows.length }} 条</span>
              </div>
              <el-table :data="incidentRows" stripe>
                <el-table-column prop="incidentNo" label="编号" min-width="140" />
                <el-table-column prop="title" label="标题" min-width="160" />
                <el-table-column prop="labName" label="实验室" min-width="140" />
                <el-table-column prop="incidentLevel" label="等级" width="110" />
                <el-table-column prop="status" label="状态" width="110" />
                <el-table-column label="操作" min-width="220">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="editIncident(row)">编辑</el-button>
                    <el-button text @click="quickIncidentStatus(row, 'processing')">转处理中</el-button>
                    <el-button text type="success" @click="quickIncidentStatus(row, 'closed')">闭环</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="应急联系人" name="contacts">
          <div class="tab-grid">
            <article class="sub-card">
              <div class="sub-head">
                <h3>联系人维护</h3>
                <span>值班电话、网络中心、保卫处、后勤等统一维护</span>
              </div>
              <el-form label-position="top">
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="姓名">
                      <el-input v-model="contactForm.name" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="岗位">
                      <el-input v-model="contactForm.roleName" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="电话">
                      <el-input v-model="contactForm.phone" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="优先级">
                      <el-input-number v-model="contactForm.priorityNo" :min="1" :max="999" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="状态">
                      <el-select v-model="contactForm.status" style="width: 100%">
                        <el-option label="启用" value="active" />
                        <el-option label="停用" value="inactive" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="说明">
                      <el-input v-model="contactForm.description" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
              <div class="action-row">
                <el-button @click="resetContactForm">清空</el-button>
                <el-button type="primary" :loading="savingContact" @click="saveContactRecord">保存联系人</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>联系人列表</h3>
                <span>{{ contactRows.length }} 条</span>
              </div>
              <el-table :data="contactRows" stripe>
                <el-table-column prop="priorityNo" label="优先级" width="90" />
                <el-table-column prop="name" label="姓名" min-width="120" />
                <el-table-column prop="roleName" label="岗位" min-width="140" />
                <el-table-column prop="phone" label="电话" min-width="140" />
                <el-table-column prop="status" label="状态" width="100" />
                <el-table-column label="操作" min-width="180">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="editContact(row)">编辑</el-button>
                    <el-button text type="danger" @click="deleteContactRecord(row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
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
  id: null,
  dutyDate: '',
  shiftName: '',
  assigneeName: '',
  assigneePhone: '',
  backupName: '',
  backupPhone: '',
  status: 'scheduled',
  note: ''
})

const incidentForm = reactive({
  id: null,
  labId: null,
  labName: '',
  title: '',
  incidentLevel: 'medium',
  status: 'reported',
  reporterName: '',
  reporterPhone: '',
  emergencyContactName: '',
  description: '',
  disposalNote: ''
})

const contactForm = reactive({
  id: null,
  name: '',
  roleName: '',
  phone: '',
  priorityNo: 10,
  status: 'active',
  description: ''
})

function resetDutyForm() {
  dutyForm.id = null
  dutyForm.dutyDate = ''
  dutyForm.shiftName = ''
  dutyForm.assigneeName = ''
  dutyForm.assigneePhone = ''
  dutyForm.backupName = ''
  dutyForm.backupPhone = ''
  dutyForm.status = 'scheduled'
  dutyForm.note = ''
}

function resetIncidentForm() {
  incidentForm.id = null
  incidentForm.labId = null
  incidentForm.labName = ''
  incidentForm.title = ''
  incidentForm.incidentLevel = 'medium'
  incidentForm.status = 'reported'
  incidentForm.reporterName = ''
  incidentForm.reporterPhone = ''
  incidentForm.emergencyContactName = ''
  incidentForm.description = ''
  incidentForm.disposalNote = ''
}

function resetContactForm() {
  contactForm.id = null
  contactForm.name = ''
  contactForm.roleName = ''
  contactForm.phone = ''
  contactForm.priorityNo = 10
  contactForm.status = 'active'
  contactForm.description = ''
}

function syncIncidentLabName() {
  const matched = labOptions.value.find((item) => Number(item.labId || item.id) === Number(incidentForm.labId || 0))
  incidentForm.labName = matched ? String(matched.labName || matched.name || '') : ''
}

async function loadAll() {
  loading.value = true
  try {
    const [labRes, dutyRes, incidentRes, contactRes] = await Promise.all([
      getLabs({ pageSize: 500 }),
      getDutyRoster({}),
      getIncidents({}),
      getEmergencyContacts({})
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
  } finally {
    savingDuty.value = false
  }
}

function editDuty(row) {
  Object.assign(dutyForm, { ...row })
}

async function quickDutyStatus(row, status) {
  await updateDutyRosterStatus(row.id, { status, note: row.note || '' })
  ElMessage.success('值班状态已更新')
  await loadAll()
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
  } finally {
    savingIncident.value = false
  }
}

function editIncident(row) {
  Object.assign(incidentForm, { ...row })
}

async function quickIncidentStatus(row, status) {
  const disposalNote = status === 'closed'
    ? `${row.disposalNote || ''}\n${new Date().toLocaleString()} 已闭环`.trim()
    : row.disposalNote || ''
  await updateIncidentStatus(row.id, {
    status,
    disposalNote
  })
  ElMessage.success('事故状态已更新')
  await loadAll()
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
  } finally {
    savingContact.value = false
  }
}

function editContact(row) {
  Object.assign(contactForm, { ...row })
}

async function deleteContactRecord(row) {
  await ElMessageBox.confirm(`确认删除联系人 ${row.name} 吗？`, '删除联系人', { type: 'warning' })
  await deleteEmergencyContact(row.id)
  ElMessage.success('联系人已删除')
  await loadAll()
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped lang="scss">
.duty-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card,
.sub-card {
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-surface);
  box-shadow: var(--app-shadow);
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(239, 68, 68, 0.12), transparent 30%),
    linear-gradient(135deg, #fff8f7 0%, #fff1ee 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hero-card h2,
.sub-head h3 {
  margin: 0;
}

.hero-copy p,
.sub-head span {
  color: var(--app-muted);
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 700;
}

.panel-card {
  padding: 24px;
}

.tab-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.sub-card {
  padding: 20px;
}

.sub-head,
.hero-actions,
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sub-head {
  align-items: flex-start;
  margin-bottom: 16px;
}

.action-row {
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .tab-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .hero-actions,
  .sub-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
