<template>
  <div class="rules-page">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">规则中心</span>
        <h2>预约规则配置</h2>
        <p>集中管理全局预约规则、实验室覆盖规则、优先级权重与候补预演。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadAll">刷新</el-button>
        <el-button type="primary" :loading="saving" @click="saveRules">保存预约规则</el-button>
      </div>
    </section>

    <section class="panel-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="预约规则" name="rules">
          <div class="grid-layout">
            <article class="sub-card">
              <div class="sub-head">
                <h3>全局规则</h3>
                <span>默认作用于所有实验室</span>
              </div>
              <div class="field-grid">
                <el-form-item label="最小提前天数">
                  <el-input-number v-model="form.global.minDaysAhead" :min="0" :max="365" />
                </el-form-item>
                <el-form-item label="最大提前天数">
                  <el-input-number v-model="form.global.maxDaysAhead" :min="0" :max="365" />
                </el-form-item>
                <el-form-item label="开始时间">
                  <el-input v-model="form.global.minTime" placeholder="08:00" />
                </el-form-item>
                <el-form-item label="结束时间">
                  <el-input v-model="form.global.maxTime" placeholder="22:00" />
                </el-form-item>
              </div>
              <el-form-item label="可预约时段">
                <el-input v-model="form.global.slotsText" type="textarea" :rows="6" placeholder="每行一个时段，例如 08:00-08:40" />
              </el-form-item>
              <el-form-item label="停用日期">
                <el-input v-model="form.global.disabledDatesText" type="textarea" :rows="4" placeholder="每行一个日期，例如 2026-03-10" />
              </el-form-item>
              <el-form-item label="审批模式">
                <el-radio-group v-model="form.global.approvalMode">
                  <el-radio-button value="auto">自动通过</el-radio-button>
                  <el-radio-button value="teacher">教师审批</el-radio-button>
                  <el-radio-button value="admin">管理员审批</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <div class="switch-row">
                <span>高峰时段强制审批</span>
                <el-switch v-model="form.global.peakForceApproval" />
              </div>
              <el-form-item label="高峰时段列表">
                <el-input v-model="form.global.peakSlotsText" type="textarea" :rows="4" placeholder="每行一个时段" />
              </el-form-item>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>实验室覆盖规则</h3>
                <span>{{ form.labRules.length }} 条</span>
              </div>
              <div class="action-row">
                <el-button @click="addLabRule">新增实验室规则</el-button>
              </div>
              <div v-if="form.labRules.length" class="lab-rule-list">
                <article v-for="(rule, index) in form.labRules" :key="`rule-${index}`" class="lab-rule-card">
                  <div class="sub-head">
                    <strong>规则 #{{ index + 1 }}</strong>
                    <el-button type="danger" text @click="removeLabRule(index)">删除</el-button>
                  </div>
                  <el-form-item label="实验室">
                    <el-select v-model="rule.labId" style="width: 100%" @change="syncLabName(rule)">
                      <el-option v-for="lab in labs" :key="lab.labId || lab.id" :label="lab.labName || lab.name" :value="lab.labId || lab.id" />
                    </el-select>
                  </el-form-item>
                  <div class="field-grid">
                    <el-form-item label="最小提前天数">
                      <el-input-number v-model="rule.minDaysAhead" :min="0" :max="365" />
                    </el-form-item>
                    <el-form-item label="最大提前天数">
                      <el-input-number v-model="rule.maxDaysAhead" :min="0" :max="365" />
                    </el-form-item>
                    <el-form-item label="开始时间">
                      <el-input v-model="rule.minTime" />
                    </el-form-item>
                    <el-form-item label="结束时间">
                      <el-input v-model="rule.maxTime" />
                    </el-form-item>
                  </div>
                  <el-form-item label="可预约时段">
                    <el-input v-model="rule.slotsText" type="textarea" :rows="4" />
                  </el-form-item>
                  <el-form-item label="停用日期">
                    <el-input v-model="rule.disabledDatesText" type="textarea" :rows="3" />
                  </el-form-item>
                  <el-form-item label="审批模式">
                    <el-radio-group v-model="rule.approvalMode">
                      <el-radio-button value="auto">自动通过</el-radio-button>
                      <el-radio-button value="teacher">教师审批</el-radio-button>
                      <el-radio-button value="admin">管理员审批</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                  <div class="switch-row">
                    <span>启用当前规则</span>
                    <el-switch v-model="rule.enabled" />
                  </div>
                  <div class="switch-row">
                    <span>高峰时段强制审批</span>
                    <el-switch v-model="rule.peakForceApproval" />
                  </div>
                  <el-form-item label="高峰时段列表">
                    <el-input v-model="rule.peakSlotsText" type="textarea" :rows="3" />
                  </el-form-item>
                </article>
              </div>
              <el-empty v-else description="当前仅使用全局规则" />
            </article>
          </div>
          <article class="sub-card borrow-card">
            <div class="sub-head">
              <h3>资产借用二次确认</h3>
              <span>把重点资产、高风险借用和逾期用户复核改成可配置策略</span>
            </div>
            <div class="field-grid borrow-grid">
              <div class="switch-row">
                <span>所有借用都要求二次确认</span>
                <el-switch v-model="form.borrowApproval.requireSecondaryConfirm" />
              </div>
              <div class="switch-row">
                <span>风险申请自动要求二次确认</span>
                <el-switch v-model="form.borrowApproval.riskFlagForceSecondaryConfirm" />
              </div>
              <div class="switch-row">
                <span>有逾期历史自动要求二次确认</span>
                <el-switch v-model="form.borrowApproval.overdueHistoryForceSecondaryConfirm" />
              </div>
            </div>
            <el-form-item label="指定实验室">
              <el-input
                v-model="form.borrowApproval.labNamesText"
                type="textarea"
                :rows="4"
                placeholder="每行一个实验室名称，命中后需要二次确认"
              />
            </el-form-item>
            <el-form-item label="指定资产关键字">
              <el-input
                v-model="form.borrowApproval.assetKeywordsText"
                type="textarea"
                :rows="4"
                placeholder="每行一个关键字，匹配资产名称或资产编号"
              />
            </el-form-item>
          </article>
        </el-tab-pane>

        <el-tab-pane label="优先级与候补" name="priority">
          <div class="grid-layout">
            <article class="sub-card">
              <div class="sub-head">
                <h3>优先级权重</h3>
                <span>影响候补排序</span>
              </div>
              <div class="field-grid">
                <el-form-item label="教师权重">
                  <el-input-number v-model="priorityRule.teacherWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="学生权重">
                  <el-input-number v-model="priorityRule.studentWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="管理员权重">
                  <el-input-number v-model="priorityRule.adminWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="默认用途权重">
                  <el-input-number v-model="priorityRule.defaultWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="教学用途权重">
                  <el-input-number v-model="priorityRule.teachingWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="科研用途权重">
                  <el-input-number v-model="priorityRule.researchWeight" :min="-100" :max="100" />
                </el-form-item>
                <el-form-item label="违约扣分">
                  <el-input-number v-model="priorityRule.violationPenalty" :min="0" :max="100" />
                </el-form-item>
                <el-form-item label="等待加分上限小时">
                  <el-input-number v-model="priorityRule.waitHourBonusCap" :min="0" :max="720" />
                </el-form-item>
                <el-form-item label="每小时等待加分">
                  <el-input-number v-model="priorityRule.waitHourBonus" :min="0" :max="10" :step="0.1" />
                </el-form-item>
              </div>
              <div class="action-row">
                <el-button type="primary" :loading="prioritySaving" @click="savePriorityRule">保存权重</el-button>
              </div>
            </article>

            <article class="sub-card">
              <div class="sub-head">
                <h3>规则预演</h3>
                <span>按实验室、日期、时段查看排序结果</span>
              </div>
              <div class="field-grid">
                <el-form-item label="实验室名称">
                  <el-input v-model="previewForm.labName" />
                </el-form-item>
                <el-form-item label="日期">
                  <el-date-picker v-model="previewForm.date" type="date" value-format="YYYY-MM-DD" />
                </el-form-item>
                <el-form-item label="时段">
                  <el-input v-model="previewForm.time" placeholder="例如 08:00-08:40" />
                </el-form-item>
              </div>
              <div class="action-row">
                <el-button :loading="previewing" @click="previewPriority">执行预演</el-button>
              </div>
              <el-table :data="previewItems" stripe>
                <el-table-column prop="userName" label="申请人" min-width="120" />
                <el-table-column prop="userRole" label="角色" min-width="100" />
                <el-table-column prop="reason" label="原因" min-width="180" />
                <el-table-column prop="priorityScore" label="优先分" min-width="100" />
                <el-table-column prop="createdAt" label="创建时间" min-width="180" />
              </el-table>
            </article>
          </div>

          <article class="panel-card waitlist-panel">
            <div class="sub-head">
              <h3>候补队列</h3>
              <div class="action-row">
                <el-button @click="loadWaitlist">刷新</el-button>
              </div>
            </div>
            <el-table :data="waitlistRows" stripe>
              <el-table-column prop="labName" label="实验室" min-width="160" />
              <el-table-column prop="date" label="日期" min-width="120" />
              <el-table-column prop="time" label="时段" min-width="140" />
              <el-table-column prop="userName" label="申请人" min-width="120" />
              <el-table-column prop="userRole" label="角色" min-width="100" />
              <el-table-column prop="priorityScore" label="优先分" min-width="100" />
              <el-table-column prop="status" label="状态" min-width="100" />
              <el-table-column label="操作" min-width="180">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'waiting'" text type="primary" @click="promoteWaitlist(row)">手动递补</el-button>
                  <el-button v-if="row.status === 'waiting'" text type="danger" @click="cancelWait(row)">取消候补</el-button>
                </template>
              </el-table-column>
            </el-table>
          </article>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import {
  cancelReservationWaitlist,
  getReservationPriorityRules,
  getReservationRules,
  getReservationWaitlist,
  previewReservationPriority,
  promoteReservationWaitlist,
  saveReservationPriorityRules,
  saveReservationRules
} from '@/api/rules'

const activeTab = ref('rules')
const loading = ref(false)
const saving = ref(false)
const prioritySaving = ref(false)
const previewing = ref(false)
const labs = ref([])
const waitlistRows = ref([])
const previewItems = ref([])

const form = reactive({
  global: emptyRuleForm(),
  labRules: [],
  borrowApproval: emptyBorrowApprovalForm()
})

const priorityRule = reactive({
  teacherWeight: 30,
  studentWeight: 10,
  adminWeight: 20,
  teachingWeight: 25,
  researchWeight: 15,
  defaultWeight: 5,
  violationPenalty: 15,
  waitHourBonus: 1,
  waitHourBonusCap: 48
})

const previewForm = reactive({
  labName: '',
  date: '',
  time: ''
})

function emptyRuleForm() {
  return {
    enabled: true,
    labId: 0,
    labName: '',
    minDaysAhead: 0,
    maxDaysAhead: 30,
    minTime: '08:00',
    maxTime: '22:00',
    slotsText: '',
    disabledDatesText: '',
    approvalMode: 'admin',
    peakForceApproval: false,
    peakSlotsText: ''
  }
}

function emptyBorrowApprovalForm() {
  return {
    requireSecondaryConfirm: false,
    riskFlagForceSecondaryConfirm: true,
    overdueHistoryForceSecondaryConfirm: true,
    labNamesText: '',
    assetKeywordsText: ''
  }
}

function splitTextList(text) {
  return String(text || '')
    .split(/[\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function toTextList(list) {
  return Array.isArray(list) ? list.map((item) => String(item || '').trim()).filter(Boolean).join('\n') : ''
}

function mapRuleForm(rule = {}) {
  const approval = rule.approval || {}
  return {
    enabled: rule.enabled !== false,
    labId: Number(rule.labId || 0),
    labName: String(rule.labName || ''),
    minDaysAhead: Number(rule.minDaysAhead || 0),
    maxDaysAhead: Number(rule.maxDaysAhead || 30),
    minTime: String(rule.minTime || '08:00'),
    maxTime: String(rule.maxTime || '22:00'),
    slotsText: toTextList(rule.slots || []),
    disabledDatesText: toTextList(rule.disabledDates || []),
    approvalMode: String(approval.mode || 'admin'),
    peakForceApproval: Boolean(approval.peakForceApproval),
    peakSlotsText: toTextList(approval.peakSlots || [])
  }
}

function mapBorrowApprovalForm(rule = {}) {
  return {
    requireSecondaryConfirm: Boolean(rule.requireSecondaryConfirm),
    riskFlagForceSecondaryConfirm: rule.riskFlagForceSecondaryConfirm !== false,
    overdueHistoryForceSecondaryConfirm: rule.overdueHistoryForceSecondaryConfirm !== false,
    labNamesText: toTextList(rule.labNames || []),
    assetKeywordsText: toTextList(rule.assetKeywords || [])
  }
}

function buildRulePayload(source) {
  return {
    minDaysAhead: Number(source.minDaysAhead || 0),
    maxDaysAhead: Number(source.maxDaysAhead || 0),
    minTime: String(source.minTime || '').trim(),
    maxTime: String(source.maxTime || '').trim(),
    slots: splitTextList(source.slotsText),
    disabledDates: splitTextList(source.disabledDatesText),
    blackoutSlots: [],
    approval: {
      mode: String(source.approvalMode || 'admin'),
      peakForceApproval: Boolean(source.peakForceApproval),
      peakSlots: splitTextList(source.peakSlotsText)
    }
  }
}

function buildBorrowApprovalPayload(source) {
  return {
    requireSecondaryConfirm: Boolean(source.requireSecondaryConfirm),
    riskFlagForceSecondaryConfirm: Boolean(source.riskFlagForceSecondaryConfirm),
    overdueHistoryForceSecondaryConfirm: Boolean(source.overdueHistoryForceSecondaryConfirm),
    labNames: splitTextList(source.labNamesText),
    assetKeywords: splitTextList(source.assetKeywordsText)
  }
}

function syncLabName(rule) {
  const matched = labs.value.find((item) => Number(item.labId || item.id) === Number(rule.labId || 0))
  rule.labName = matched ? String(matched.labName || matched.name || '') : ''
}

function addLabRule() {
  form.labRules.push(emptyRuleForm())
}

function removeLabRule(index) {
  form.labRules.splice(index, 1)
}

async function loadRules() {
  const response = await getReservationRules()
  const data = response.data?.data || {}
  labs.value = Array.isArray(data.labs) ? data.labs : []
  form.global = mapRuleForm(data.global || {})
  form.labRules = Array.isArray(data.labRules) ? data.labRules.map((item) => mapRuleForm(item)) : []
  form.borrowApproval = mapBorrowApprovalForm(data.borrowApproval || {})
}

async function loadPriorityRules() {
  const response = await getReservationPriorityRules()
  Object.assign(priorityRule, response.data?.data || {})
}

async function loadWaitlist() {
  const response = await getReservationWaitlist({
    mine: 0,
    status: 'waiting'
  })
  waitlistRows.value = Array.isArray(response.data?.data) ? response.data.data : []
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadRules(), loadPriorityRules(), loadWaitlist()])
  } finally {
    loading.value = false
  }
}

async function saveRules() {
  if (Number(form.global.minDaysAhead || 0) > Number(form.global.maxDaysAhead || 0)) {
    ElMessage.warning('全局最小提前天数不能大于最大提前天数')
    return
  }

  saving.value = true
  try {
    const payload = {
      global: buildRulePayload(form.global),
      labRules: form.labRules.map((rule) => ({
        ...buildRulePayload(rule),
        enabled: Boolean(rule.enabled),
        labId: Number(rule.labId || 0),
        labName: String(rule.labName || '')
      })),
      borrowApproval: buildBorrowApprovalPayload(form.borrowApproval)
    }
    await saveReservationRules(payload)
    ElMessage.success('预约规则已保存')
    await loadRules()
  } finally {
    saving.value = false
  }
}

async function savePriorityRule() {
  prioritySaving.value = true
  try {
    await saveReservationPriorityRules({ ...priorityRule })
    ElMessage.success('优先级权重已保存')
    await loadPriorityRules()
  } finally {
    prioritySaving.value = false
  }
}

async function previewPriority() {
  if (!previewForm.labName || !previewForm.date || !previewForm.time) {
    ElMessage.warning('请填写实验室、日期和时段')
    return
  }
  previewing.value = true
  try {
    const response = await previewReservationPriority({
      ...previewForm,
      rule: { ...priorityRule }
    })
    previewItems.value = Array.isArray(response.data?.data?.items) ? response.data.data.items : []
  } finally {
    previewing.value = false
  }
}

async function promoteWaitlist(row) {
  await promoteReservationWaitlist(row.id)
  ElMessage.success('候补已递补')
  await loadWaitlist()
}

async function cancelWait(row) {
  await cancelReservationWaitlist(row.id)
  ElMessage.success('候补已取消')
  await loadWaitlist()
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped lang="scss">
.rules-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.panel-card,
.sub-card,
.lab-rule-card {
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
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.16), transparent 30%),
    linear-gradient(135deg, #fffaf5 0%, #fff3ea 100%);
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

.hero-card p,
.sub-head span {
  color: var(--app-muted);
}

.hero-actions,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: #ffedd5;
  color: #c2410c;
  font-size: 12px;
  font-weight: 700;
}

.panel-card {
  padding: 24px;
}

.grid-layout,
.field-grid {
  display: grid;
  gap: 20px;
}

.grid-layout {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sub-card {
  padding: 20px;
}

.sub-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.lab-rule-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lab-rule-card {
  padding: 18px;
  background: #f8fafc;
}

.waitlist-panel {
  margin-top: 20px;
}

.borrow-card {
  margin-top: 20px;
}

.borrow-grid {
  margin-bottom: 18px;
}

@media (max-width: 1200px) {
  .grid-layout,
  .field-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-card,
  .hero-actions,
  .sub-head,
  .switch-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
