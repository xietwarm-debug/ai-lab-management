<template>
  <div class="asset-page">
    <section class="hero-card">
      <div>
        <span class="eyebrow">资产生命周期</span>
        <h2>资产管理工作台</h2>
        <p>补齐采购入库、维保计划、维修历史、二维码打印、责任人变更和折旧报废。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="refreshAll">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">采购入库</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card"><span>资产总数</span><strong>{{ summary.total }}</strong></article>
      <article class="metric-card"><span>借出中</span><strong>{{ summary.borrowed }}</strong></article>
      <article class="metric-card"><span>维保到期</span><strong>{{ summary.maintenanceDue }}</strong></article>
      <article class="metric-card"><span>已报废</span><strong>{{ summary.scrapped }}</strong></article>
    </section>

    <section class="panel-card">
      <el-form inline>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="资产编号 / 名称 / 实验室 / 责任人" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="在用" value="in_service" />
            <el-option label="维修中" value="repairing" />
            <el-option label="已报废" value="scrapped" />
          </el-select>
        </el-form-item>
        <el-form-item label="生命周期">
          <el-select v-model="filters.lifecycle" style="width: 180px" clearable>
            <el-option label="全部" value="" />
            <el-option label="借出中" value="borrowed" />
            <el-option label="维保到期" value="maintenance_due" />
            <el-option label="质保到期" value="warranty_due" />
            <el-option label="已报废" value="scrapped" />
          </el-select>
        </el-form-item>
        <el-form-item label="实验室">
          <el-select v-model="filters.labId" style="width: 180px" clearable>
            <el-option label="全部" value="" />
            <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="dueRows.length" class="panel-card">
      <div class="panel-head">
        <h3>30 天内维保待办</h3>
        <el-button text @click="fetchDueRows">刷新</el-button>
      </div>
      <div class="due-list">
        <article v-for="item in dueRows" :key="item.id" class="due-card">
          <strong>{{ item.assetCode || '-' }} · {{ item.name || '-' }}</strong>
          <p>{{ item.labName || '-' }}</p>
          <p>下次保养 {{ item.nextMaintenanceAt || '-' }}</p>
          <p>质保到期 {{ item.warrantyUntil || '-' }}</p>
        </article>
      </div>
    </section>

    <section class="panel-card">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="assetCode" label="资产编号" min-width="140" />
        <el-table-column prop="name" label="资产名称" min-width="160" />
        <el-table-column prop="labName" label="实验室" min-width="140" />
        <el-table-column prop="keeper" label="责任人" min-width="120" />
        <el-table-column prop="purchaseDate" label="采购日期" min-width="120" />
        <el-table-column label="采购金额" min-width="120">
          <template #default="{ row }">{{ money(row.price) }}</template>
        </el-table-column>
        <el-table-column label="折旧" min-width="150">
          <template #default="{ row }">{{ depreciationText(row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="nextMaintenanceAt" label="下次保养" min-width="160" />
        <el-table-column label="操作" min-width="420" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link @click="openKeeperDialog(row)">责任人</el-button>
            <el-button link @click="openMaintenanceDialog(row)">维保计划</el-button>
            <el-button link @click="openHistory(row)">维修历史</el-button>
            <el-button link @click="openCodeDialog(row)">资产码</el-button>
            <el-button link type="danger" @click="openScrapDialog(row)">报废</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50]"
          :total="total"
          @current-change="fetchRows"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>

    <el-dialog v-model="dialogVisible" title="采购入库" width="720px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="资产编号"><el-input v-model="form.assetCode" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="资产名称"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="实验室">
              <el-select v-model="form.labId" style="width: 100%" @change="syncLabName">
                <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="责任人"><el-input v-model="form.keeper" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="form.brand" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号"><el-input v-model="form.model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="采购日期"><el-date-picker v-model="form.purchaseDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="采购金额"><el-input v-model="form.price" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="允许借用"><el-switch v-model="form.allowBorrow" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="规格 JSON"><el-input v-model="form.specJson" type="textarea" :rows="3" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="maintenanceVisible" title="维保计划" width="620px">
      <el-form label-position="top">
        <el-form-item label="下次保养时间"><el-date-picker v-model="maintenanceForm.nextMaintenanceAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
        <el-form-item label="维保周期（天）"><el-input-number v-model="maintenanceForm.maintenanceCycleDays" :min="1" :max="3650" /></el-form-item>
        <el-form-item label="质保到期"><el-date-picker v-model="maintenanceForm.warrantyUntil" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="位置备注"><el-input v-model="maintenanceForm.locationNote" /></el-form-item>
        <el-form-item label="条码值"><el-input v-model="maintenanceForm.barcodeValue" /></el-form-item>
        <el-form-item label="维保说明"><el-input v-model="maintenanceForm.maintenanceNote" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="同步记录为已保养"><el-switch v-model="maintenanceForm.markMaintained" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="maintenanceVisible = false">取消</el-button>
        <el-button type="primary" :loading="maintenanceSaving" @click="submitMaintenance">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="keeperVisible" title="责任人变更" width="520px">
      <el-form label-position="top">
        <el-form-item label="责任人"><el-input v-model="keeperForm.keeper" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="keeperVisible = false">取消</el-button>
        <el-button type="primary" :loading="keeperSaving" @click="submitKeeper">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="scrapVisible" title="报废登记" width="520px">
      <el-form label-position="top">
        <el-form-item label="报废原因"><el-input v-model="scrapForm.reason" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scrapVisible = false">取消</el-button>
        <el-button type="danger" :loading="scrapSaving" @click="submitScrap">确认报废</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="资产详情" size="560px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="资产编号">{{ detail.assetCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ detail.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="实验室">{{ detail.labName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ detail.keeper || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购日期">{{ detail.purchaseDate || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购金额">{{ money(detail.price) }}</el-descriptions-item>
        <el-descriptions-item label="折旧估算">{{ depreciationText(detail) }}</el-descriptions-item>
        <el-descriptions-item label="预计净值">{{ money(depreciationMeta(detail).residualValue) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="下次保养">{{ detail.nextMaintenanceAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近保养">{{ detail.lastMaintainedAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="质保到期">{{ detail.warrantyUntil || '-' }}</el-descriptions-item>
        <el-descriptions-item label="条码值">{{ detail.barcodeValue || '-' }}</el-descriptions-item>
        <el-descriptions-item label="报废原因">{{ detail.scrapReason || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无资产详情" />
    </el-drawer>

    <el-drawer v-model="historyVisible" title="维修与维保历史" size="720px">
      <div class="panel-head">
        <strong>{{ historyTarget?.assetCode || '-' }} · {{ historyTarget?.name || '-' }}</strong>
        <el-button type="primary" @click="openRepairDialog">登记维修</el-button>
      </div>
      <div v-if="timelineRows.length" class="timeline-list">
        <article v-for="item in timelineRows" :key="item.key" class="timeline-card">
          <div class="panel-head"><strong>{{ item.title }}</strong><span>{{ item.time }}</span></div>
          <p>{{ item.subtitle }}</p>
          <p>{{ item.detail }}</p>
        </article>
      </div>
      <el-empty v-else description="暂无维修与维保记录" />
    </el-drawer>

    <el-dialog v-model="repairVisible" title="登记维修" width="620px">
      <el-form label-position="top">
        <el-form-item label="故障类型">
          <el-select v-model="repairForm.issueType" style="width: 100%">
            <el-option label="网络问题" value="network" />
            <el-option label="硬件问题" value="hardware" />
            <el-option label="软件问题" value="software" />
            <el-option label="外设问题" value="peripheral" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="简述"><el-input v-model="repairForm.note" /></el-form-item>
        <el-form-item label="维修说明"><el-input v-model="repairForm.description" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairVisible = false">取消</el-button>
        <el-button type="primary" :loading="repairSaving" @click="submitRepair">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="codeVisible" title="二维码 / 条码打印" width="620px">
      <div v-if="codeData" class="due-list">
        <article class="due-card"><strong>资产编号</strong><p>{{ codeData.assetCode || '-' }}</p></article>
        <article class="due-card"><strong>二维码内容</strong><p>{{ codeData.qrText || '-' }}</p></article>
        <article class="due-card"><strong>条码内容</strong><p>{{ codeData.barcodeValue || '-' }}</p></article>
      </div>
      <div class="hero-actions" style="margin-top: 16px">
        <el-button @click="copyText(codeData?.qrText)">复制二维码内容</el-button>
        <el-button @click="copyText(codeData?.barcodeValue)">复制条码内容</el-button>
        <el-button type="primary" @click="printCode">打印资产码</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { createEquipment, createEquipmentEvent, getDueMaintenanceEquipments, getEquipmentCode, getEquipmentDetail, getEquipmentEvents, getEquipmentList, scrapEquipment, updateEquipment, updateEquipmentMaintenancePlan } from '@/api/equipments'
import { getLabs } from '@/api/labs'
import { getRepairOrders } from '@/api/repairs'

const loading = ref(false)
const saving = ref(false)
const maintenanceSaving = ref(false)
const keeperSaving = ref(false)
const scrapSaving = ref(false)
const repairSaving = ref(false)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const labs = ref([])
const dueRows = ref([])
const detail = ref(null)
const historyTarget = ref(null)
const codeData = ref(null)
const eventRows = ref([])
const repairRows = ref([])
const dialogVisible = ref(false)
const maintenanceVisible = ref(false)
const keeperVisible = ref(false)
const scrapVisible = ref(false)
const detailVisible = ref(false)
const historyVisible = ref(false)
const repairVisible = ref(false)
const codeVisible = ref(false)

const summary = reactive({ total: 0, borrowed: 0, maintenanceDue: 0, scrapped: 0 })
const filters = reactive({ keyword: '', status: '', lifecycle: '', labId: '' })
const form = reactive({ assetCode: '', name: '', labId: undefined, labName: '', keeper: '', brand: '', model: '', purchaseDate: '', price: '', specJson: '', allowBorrow: false })
const maintenanceForm = reactive({ id: 0, nextMaintenanceAt: '', maintenanceCycleDays: 180, maintenanceNote: '', warrantyUntil: '', locationNote: '', barcodeValue: '', markMaintained: false })
const keeperForm = reactive({ id: 0, keeper: '' })
const scrapForm = reactive({ id: 0, reason: '' })
const repairForm = reactive({ issueType: 'hardware', note: '', description: '' })

const timelineRows = computed(() => [...eventRows.value.map((item) => ({ key: `event-${item.id}`, title: eventLabel(item.eventType), subtitle: `操作人 ${item.operatorName || '-'}`, detail: item.note || '无附加说明', time: item.createdAt || '' })), ...repairRows.value.map((item) => ({ key: `repair-${item.id}`, title: `维修工单 ${item.orderNo || `#${item.id}`}`, subtitle: `状态 ${repairStatus(item.status)} · 指派 ${item.assigneeName || '-'}`, detail: item.description || '无工单描述', time: item.updatedAt || item.submittedAt || '' }))].sort((a, b) => timeValue(b.time) - timeValue(a.time)))

function timeValue(value) { const n = Date.parse(String(value || '').trim().replace(' ', 'T')); return Number.isFinite(n) ? n : 0 }
function numberValue(value) { const n = Number(value); return Number.isFinite(n) ? n : 0 }
function statusText(status) { return status === 'repairing' ? '维修中' : status === 'scrapped' ? '已报废' : '在用' }
function statusType(status) { return status === 'repairing' ? 'warning' : status === 'scrapped' ? 'danger' : 'success' }
function repairStatus(status) { return status === 'accepted' ? '已受理' : status === 'processing' ? '处理中' : status === 'completed' ? '已完成' : '已提交' }
function eventLabel(type) { return type === 'maintain' ? '维修登记' : type === 'maint_plan' ? '维保计划更新' : type === 'scrap' ? '资产报废' : type || '事件记录' }
function money(value) { return `¥${numberValue(value).toFixed(2)}` }
function depreciationMeta(row) { const price = numberValue(row?.price); const purchaseAt = Date.parse(String(row?.purchaseDate || '').trim()); if (!price || !Number.isFinite(purchaseAt)) return { residualValue: 0, progress: 0 }; const progress = Math.min(Math.max((Date.now() - purchaseAt) / (365 * 5 * 24 * 60 * 60 * 1000), 0), 1); return { residualValue: price * (1 - progress), progress } }
function depreciationText(row) { return numberValue(row?.price) ? `${(depreciationMeta(row).progress * 100).toFixed(0)}% · 净值 ${money(depreciationMeta(row).residualValue)}` : '未录入金额' }
function syncLabName(value) { const target = labs.value.find((item) => Number(item.id) === Number(value)); form.labName = target?.name || '' }
function payloadFromDetail(row, overrides = {}) { return { assetCode: row.assetCode || '', name: row.name || '', model: row.model || '', brand: row.brand || '', labId: row.labId, labName: row.labName || '', status: row.status || 'in_service', keeper: row.keeper || '', purchaseDate: row.purchaseDate || '', price: row.price != null ? row.price : '', specJson: row.specJson || '', imageUrl: row.imageUrl || '', allowBorrow: Boolean(row.allowBorrow), ...overrides } }

async function fetchLabs() { const response = await getLabs(); labs.value = Array.isArray(response.data?.data) ? response.data.data : [] }
async function fetchDueRows() { const response = await getDueMaintenanceEquipments({ days: 30, limit: 8 }); dueRows.value = Array.isArray(response.data?.data) ? response.data.data : [] }
async function fetchSummary() { const [a, b, c, d] = await Promise.all([getEquipmentList({ page: 1, pageSize: 1 }), getEquipmentList({ page: 1, pageSize: 1, lifecycle: 'borrowed' }), getEquipmentList({ page: 1, pageSize: 1, maintenanceDueDays: 30 }), getEquipmentList({ page: 1, pageSize: 1, status: 'scrapped' })]); summary.total = Number(a.data?.meta?.total || 0); summary.borrowed = Number(b.data?.meta?.total || 0); summary.maintenanceDue = Number(c.data?.meta?.total || 0); summary.scrapped = Number(d.data?.meta?.total || 0) }
async function fetchRows() { loading.value = true; try { const response = await getEquipmentList({ page: page.value, pageSize: pageSize.value, keyword: filters.keyword, status: filters.status, lifecycle: filters.lifecycle, labId: filters.labId }); rows.value = Array.isArray(response.data?.data) ? response.data.data : []; total.value = Number(response.data?.meta?.total || 0) } finally { loading.value = false } }
async function refreshAll() { await Promise.all([fetchRows(), fetchSummary(), fetchDueRows()]) }
function handleSearch() { page.value = 1; fetchRows() }
function resetFilters() { filters.keyword = ''; filters.status = ''; filters.lifecycle = ''; filters.labId = ''; handleSearch() }
function handlePageSizeChange(size) { pageSize.value = size; page.value = 1; fetchRows() }
function openCreateDialog() { form.assetCode = ''; form.name = ''; form.labId = undefined; form.labName = ''; form.keeper = ''; form.brand = ''; form.model = ''; form.purchaseDate = ''; form.price = ''; form.specJson = ''; form.allowBorrow = false; dialogVisible.value = true }
async function submitCreate() { if (!form.assetCode.trim() || !form.name.trim() || !form.labId || !form.labName) { ElMessage.warning('请填写资产编号、名称并选择实验室'); return } saving.value = true; try { await createEquipment({ assetCode: form.assetCode.trim(), name: form.name.trim(), labId: form.labId, labName: form.labName.trim(), keeper: form.keeper.trim(), brand: form.brand.trim(), model: form.model.trim(), purchaseDate: form.purchaseDate, price: form.price ? Number(form.price) : '', specJson: form.specJson.trim(), imageUrl: '', status: 'in_service', allowBorrow: form.allowBorrow }); dialogVisible.value = false; ElMessage.success('采购入库完成'); await refreshAll() } finally { saving.value = false } }
async function openDetail(row) { const response = await getEquipmentDetail(row.id); detail.value = response.data?.data || null; detailVisible.value = true }
async function openMaintenanceDialog(row) { const response = await getEquipmentDetail(row.id); detail.value = response.data?.data || null; if (!detail.value) return; maintenanceForm.id = detail.value.id; maintenanceForm.nextMaintenanceAt = detail.value.nextMaintenanceAt || ''; maintenanceForm.maintenanceCycleDays = Number(detail.value.maintenanceCycleDays || 180); maintenanceForm.maintenanceNote = detail.value.maintenanceNote || ''; maintenanceForm.warrantyUntil = detail.value.warrantyUntil || ''; maintenanceForm.locationNote = detail.value.locationNote || ''; maintenanceForm.barcodeValue = detail.value.barcodeValue || ''; maintenanceForm.markMaintained = false; maintenanceVisible.value = true }
async function submitMaintenance() { maintenanceSaving.value = true; try { await updateEquipmentMaintenancePlan(maintenanceForm.id, { nextMaintenanceAt: maintenanceForm.nextMaintenanceAt, maintenanceCycleDays: maintenanceForm.maintenanceCycleDays, maintenanceNote: maintenanceForm.maintenanceNote, warrantyUntil: maintenanceForm.warrantyUntil, locationNote: maintenanceForm.locationNote, barcodeValue: maintenanceForm.barcodeValue, markMaintained: maintenanceForm.markMaintained }); maintenanceVisible.value = false; ElMessage.success('维保计划已更新'); await refreshAll() } finally { maintenanceSaving.value = false } }
async function openKeeperDialog(row) { const response = await getEquipmentDetail(row.id); detail.value = response.data?.data || null; if (!detail.value) return; keeperForm.id = detail.value.id; keeperForm.keeper = detail.value.keeper || ''; keeperVisible.value = true }
async function submitKeeper() { if (!detail.value) return; keeperSaving.value = true; try { await updateEquipment(detail.value.id, payloadFromDetail(detail.value, { keeper: keeperForm.keeper.trim() })); keeperVisible.value = false; ElMessage.success('责任人已变更'); await refreshAll() } finally { keeperSaving.value = false } }
function openScrapDialog(row) { scrapForm.id = Number(row.id || 0); scrapForm.reason = ''; scrapVisible.value = true }
async function submitScrap() { if (!scrapForm.reason.trim()) { ElMessage.warning('请输入报废原因'); return } scrapSaving.value = true; try { await scrapEquipment(scrapForm.id, { reason: scrapForm.reason.trim() }); scrapVisible.value = false; ElMessage.success('资产已报废'); await refreshAll() } finally { scrapSaving.value = false } }
async function openHistory(row) { historyTarget.value = row; historyVisible.value = true; const [eventsResp, repairsResp] = await Promise.all([getEquipmentEvents(row.id, { page: 1, pageSize: 50 }), getRepairOrders({ equipmentId: row.id, page: 1, pageSize: 50 })]); eventRows.value = Array.isArray(eventsResp.data?.data) ? eventsResp.data.data : []; repairRows.value = Array.isArray(repairsResp.data?.data) ? repairsResp.data.data : [] }
function openRepairDialog() { repairForm.issueType = 'hardware'; repairForm.note = ''; repairForm.description = ''; repairVisible.value = true }
async function submitRepair() { if (!historyTarget.value?.id) return; if (!repairForm.note.trim() && !repairForm.description.trim()) { ElMessage.warning('请填写维修说明'); return } repairSaving.value = true; try { await createEquipmentEvent(historyTarget.value.id, { eventType: 'maintain', issueType: repairForm.issueType, note: repairForm.note.trim(), description: repairForm.description.trim() || repairForm.note.trim() }); repairVisible.value = false; ElMessage.success('维修登记已生成'); await openHistory(historyTarget.value); await refreshAll() } finally { repairSaving.value = false } }
async function openCodeDialog(row) { const response = await getEquipmentCode(row.id); codeData.value = response.data?.data || null; codeVisible.value = true }
async function copyText(value) { const text = String(value || '').trim(); if (!text) return; if (navigator?.clipboard?.writeText) { await navigator.clipboard.writeText(text); ElMessage.success('已复制') } }
function printCode() { if (!codeData.value) return; const win = window.open('', '_blank', 'width=640,height=720'); if (!win) return; win.document.write(`<html><body style="font-family:Arial;padding:24px"><h2>${codeData.value.assetCode || '-'}</h2><p>二维码内容：${codeData.value.qrText || '-'}</p><p>条码内容：${codeData.value.barcodeValue || '-'}</p></body></html>`); win.document.close(); win.print() }

onMounted(async () => { await fetchLabs(); await refreshAll() })
</script>

<style scoped lang="scss">
.asset-page { display: flex; flex-direction: column; gap: 18px; }
.hero-card, .panel-card, .metric-card, .due-card, .timeline-card { padding: 24px; border: 1px solid var(--app-border); border-radius: 24px; background: var(--app-surface); box-shadow: var(--app-shadow); }
.hero-card, .hero-actions, .panel-head, .pager-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.hero-card, .panel-head, .hero-actions { flex-wrap: wrap; }
.eyebrow { display: inline-flex; margin-bottom: 8px; color: #166534; font-size: 13px; letter-spacing: 0.08em; }
.metric-grid, .due-list, .timeline-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.metric-card span, .due-card p, .timeline-card p { color: var(--app-text-secondary); }
.metric-card strong { display: block; margin-top: 8px; font-size: 32px; }
.timeline-list { margin-top: 16px; }
@media (max-width: 960px) { .hero-card, .hero-actions, .panel-head { flex-direction: column; align-items: flex-start; } }
</style>
