<template>
  <view class="container dutyPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">值班与应急处置</view>
            <view class="subtitle">统一处理值班安排、事故处置与应急联系人</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadAll">刷新</button>
        </view>
        <view class="heroMeta muted">当前账号：{{ operator || "-" }}</view>
        <view class="heroMeta muted">值班 {{ dutyRows.length }} 条 · 事故 {{ incidentRows.length }} 条 · 联系人 {{ contactRows.length }} 条</view>
      </view>

      <view class="card">
        <view class="tabRow">
          <view
            v-for="item in tabs"
            :key="item.key"
            class="tabChip"
            :class="{ tabChipOn: activeTab === item.key }"
            @click="activeTab = item.key"
          >
            {{ item.label }}
          </view>
        </view>
      </view>

      <view v-if="activeTab === 'duty'" class="stack">
        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">{{ dutyForm.id ? "编辑值班" : "新增值班" }}</view>
            <view class="muted">支持白班/晚班/周末排班</view>
          </view>
          <picker mode="date" :value="dutyForm.dutyDate" @change="onDutyDateChange">
            <view class="pickerLike">{{ dutyForm.dutyDate || "选择日期" }}</view>
          </picker>
          <input class="inputBase mt8" v-model.trim="dutyForm.shiftName" placeholder="班次，如：白班 / 晚班" />
          <view class="rowBetween mt8">
            <input class="inputBase field" v-model.trim="dutyForm.assigneeName" placeholder="值班人" />
            <input class="inputBase field" v-model.trim="dutyForm.assigneePhone" placeholder="值班电话" />
          </view>
          <view class="rowBetween mt8">
            <input class="inputBase field" v-model.trim="dutyForm.backupName" placeholder="备岗人" />
            <input class="inputBase field" v-model.trim="dutyForm.backupPhone" placeholder="备岗电话" />
          </view>
          <view class="chipRow mt8">
            <view
              v-for="item in dutyStatusOptions"
              :key="item.value"
              class="chip"
              :class="{ chipOn: dutyForm.status === item.value }"
              @click="dutyForm.status = item.value"
            >
              {{ item.label }}
            </view>
          </view>
          <textarea class="textareaBase mt8" v-model.trim="dutyForm.note" placeholder="备注，如交接事项"></textarea>
          <view class="actionRow">
            <button class="btnSecondary miniBtn" size="mini" @click="resetDutyForm">清空</button>
            <button class="btnPrimary miniBtn" size="mini" :loading="savingDuty" @click="saveDuty">保存值班</button>
          </view>
        </view>

        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">值班列表</view>
            <view class="muted">{{ dutyRows.length }} 条</view>
          </view>
          <view v-if="dutyRows.length === 0" class="empty">暂无值班记录</view>
          <view v-else class="list">
            <view class="rowItem" v-for="item in dutyRows" :key="'duty-' + item.id">
              <view class="rowBetween">
                <view>
                  <view class="rowTitle">{{ item.dutyDate || "-" }} · {{ item.shiftName || "-" }}</view>
                  <view class="rowMeta">值班：{{ item.assigneeName || "-" }} {{ item.assigneePhone || "" }}</view>
                  <view class="rowMeta" v-if="item.backupName || item.backupPhone">备岗：{{ item.backupName || "-" }} {{ item.backupPhone || "" }}</view>
                  <view class="rowMeta" v-if="item.note">备注：{{ item.note }}</view>
                </view>
                <view class="statusTag" :class="dutyTone(item.status)">{{ dutyStatusText(item.status) }}</view>
              </view>
              <view class="actionRow">
                <button class="btnGhost miniBtn" size="mini" @click="editDuty(item)">编辑</button>
                <button
                  v-if="item.status !== 'on_duty'"
                  class="btnWarning miniBtn"
                  size="mini"
                  @click="quickDutyStatus(item, 'on_duty')"
                >
                  值班中
                </button>
                <button
                  v-if="item.status !== 'completed'"
                  class="btnPrimary miniBtn"
                  size="mini"
                  @click="quickDutyStatus(item, 'completed')"
                >
                  已完成
                </button>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="activeTab === 'incident'" class="stack">
        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">{{ incidentForm.id ? "编辑事故" : "事故上报" }}</view>
            <view class="muted">支持异常事件闭环处置</view>
          </view>
          <picker :range="labOptions" range-key="name" :value="incidentLabIndex" @change="onIncidentLabChange">
            <view class="pickerLike">{{ incidentLabText }}</view>
          </picker>
          <input class="inputBase mt8" v-model.trim="incidentForm.title" placeholder="事故标题" />
          <view class="chipRow mt8">
            <view
              v-for="item in incidentLevelOptions"
              :key="item.value"
              class="chip"
              :class="{ chipOn: incidentForm.incidentLevel === item.value }"
              @click="incidentForm.incidentLevel = item.value"
            >
              {{ item.label }}
            </view>
          </view>
          <view class="chipRow mt8">
            <view
              v-for="item in incidentStatusOptions"
              :key="item.value"
              class="chip"
              :class="{ chipOn: incidentForm.status === item.value }"
              @click="incidentForm.status = item.value"
            >
              {{ item.label }}
            </view>
          </view>
          <view class="rowBetween mt8">
            <input class="inputBase field" v-model.trim="incidentForm.reporterName" placeholder="上报人" />
            <input class="inputBase field" v-model.trim="incidentForm.reporterPhone" placeholder="联系电话" />
          </view>
          <textarea class="textareaBase mt8" v-model.trim="incidentForm.description" placeholder="事件描述"></textarea>
          <textarea class="textareaBase mt8" v-model.trim="incidentForm.disposalNote" placeholder="处置记录"></textarea>
          <view class="actionRow">
            <button class="btnSecondary miniBtn" size="mini" @click="resetIncidentForm">清空</button>
            <button class="btnDanger miniBtn" size="mini" :loading="savingIncident" @click="saveIncidentRecord">保存事故</button>
          </view>
        </view>

        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">事故列表</view>
            <view class="muted">{{ incidentRows.length }} 条</view>
          </view>
          <view v-if="incidentRows.length === 0" class="empty">暂无事故记录</view>
          <view v-else class="list">
            <view class="rowItem" v-for="item in incidentRows" :key="'incident-' + item.id">
              <view class="rowBetween">
                <view>
                  <view class="rowTitle">
                    <text class="severityDot" :class="'level-' + String(item.incidentLevel || 'medium')"></text>
                    {{ item.title || "-" }}
                  </view>
                  <view class="rowMeta">{{ item.labName || "未关联实验室" }} · {{ levelText(item.incidentLevel) }}</view>
                  <view class="rowMeta">上报：{{ item.reporterName || "-" }} {{ item.reporterPhone || "" }}</view>
                  <view class="rowMeta" v-if="item.description">描述：{{ item.description }}</view>
                  <view class="rowMeta" v-if="item.disposalNote">处置：{{ item.disposalNote }}</view>
                </view>
                <view class="statusTag" :class="incidentTone(item.status)">{{ incidentStatusText(item.status) }}</view>
              </view>
              <view class="actionRow">
                <button class="btnGhost miniBtn" size="mini" @click="editIncident(item)">编辑</button>
                <button
                  v-if="item.status !== 'processing' && item.status !== 'closed'"
                  class="btnWarning miniBtn"
                  size="mini"
                  @click="quickIncidentStatus(item, 'processing')"
                >
                  处理中
                </button>
                <button
                  v-if="item.status !== 'closed'"
                  class="btnPrimary miniBtn"
                  size="mini"
                  @click="quickIncidentStatus(item, 'closed')"
                >
                  已闭环
                </button>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view v-if="activeTab === 'contacts'" class="stack">
        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">{{ contactForm.id ? "编辑联系人" : "新增联系人" }}</view>
            <view class="muted">值班、保卫、后勤统一维护</view>
          </view>
          <input class="inputBase mt8" v-model.trim="contactForm.name" placeholder="姓名 / 部门" />
          <input class="inputBase mt8" v-model.trim="contactForm.roleName" placeholder="岗位 / 职责" />
          <view class="rowBetween mt8">
            <input class="inputBase field" v-model.trim="contactForm.phone" placeholder="电话" />
            <input class="inputBase field" v-model.number="contactForm.priorityNo" type="number" placeholder="优先级" />
          </view>
          <view class="chipRow mt8">
            <view
              v-for="item in contactStatusOptions"
              :key="item.value"
              class="chip"
              :class="{ chipOn: contactForm.status === item.value }"
              @click="contactForm.status = item.value"
            >
              {{ item.label }}
            </view>
          </view>
          <textarea class="textareaBase mt8" v-model.trim="contactForm.description" placeholder="补充说明，如 24 小时值守"></textarea>
          <view class="actionRow">
            <button class="btnSecondary miniBtn" size="mini" @click="resetContactForm">清空</button>
            <button class="btnPrimary miniBtn" size="mini" :loading="savingContact" @click="saveContactRecord">保存联系人</button>
          </view>
        </view>

        <view class="card sectionCard">
          <view class="rowBetween sectionHeader">
            <view class="cardTitle">联系人名单</view>
            <view class="muted">{{ contactRows.length }} 条</view>
          </view>
          <view v-if="contactRows.length === 0" class="empty">暂无联系人</view>
          <view v-else class="list">
            <view class="rowItem" v-for="item in contactRows" :key="'contact-' + item.id">
              <view class="rowBetween">
                <view>
                  <view class="rowTitle">{{ item.priorityNo || "-" }} · {{ item.name || "-" }}</view>
                  <view class="rowMeta">{{ item.roleName || "-" }}</view>
                  <view class="rowMeta">电话：{{ item.phone || "-" }}</view>
                  <view class="rowMeta" v-if="item.description">{{ item.description }}</view>
                </view>
                <view class="statusTag" :class="item.status === 'active' ? 'status-success' : 'status-muted'">
                  {{ item.status === "active" ? "启用" : "停用" }}
                </view>
              </view>
              <view class="actionRow">
                <button class="btnGhost miniBtn" size="mini" @click="editContact(item)">编辑</button>
                <button class="btnPrimary miniBtn" size="mini" @click="callContact(item.phone)">拨号</button>
                <button class="btnDanger miniBtn" size="mini" @click="deleteContactRecord(item)">删除</button>
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminDeleteEmergencyContact,
  adminGetDutyRoster,
  adminGetEmergencyContacts,
  adminGetIncidents,
  adminSaveDutyRoster,
  adminSaveEmergencyContact,
  adminSaveIncident,
  adminUpdateDutyRosterStatus,
  adminUpdateIncidentStatus,
  listLabs
} from "@/common/api.js"

function ensureAdmin() {
  const s = uni.getStorageSync("session")
  return !!(s && s.role === "admin")
}

function sortByPriorityAsc(rows = []) {
  return rows.slice().sort((a, b) => Number(a.priorityNo || 999) - Number(b.priorityNo || 999))
}

export default {
  data() {
    return {
      operator: "",
      loading: false,
      activeTab: "duty",
      savingDuty: false,
      savingIncident: false,
      savingContact: false,
      dutyRows: [],
      incidentRows: [],
      contactRows: [],
      labOptions: [],
      tabs: [
        { key: "duty", label: "值班表" },
        { key: "incident", label: "事故处置" },
        { key: "contacts", label: "应急联系人" }
      ],
      dutyStatusOptions: [
        { label: "待值班", value: "scheduled" },
        { label: "值班中", value: "on_duty" },
        { label: "已完成", value: "completed" },
        { label: "已关闭", value: "closed" }
      ],
      incidentLevelOptions: [
        { label: "低", value: "low" },
        { label: "中", value: "medium" },
        { label: "高", value: "high" },
        { label: "严重", value: "critical" }
      ],
      incidentStatusOptions: [
        { label: "已上报", value: "reported" },
        { label: "处理中", value: "processing" },
        { label: "已闭环", value: "closed" }
      ],
      contactStatusOptions: [
        { label: "启用", value: "active" },
        { label: "停用", value: "inactive" }
      ],
      dutyForm: {
        id: null,
        dutyDate: "",
        shiftName: "",
        assigneeName: "",
        assigneePhone: "",
        backupName: "",
        backupPhone: "",
        status: "scheduled",
        note: ""
      },
      incidentForm: {
        id: null,
        labId: 0,
        labName: "",
        title: "",
        incidentLevel: "medium",
        status: "reported",
        reporterName: "",
        reporterPhone: "",
        description: "",
        disposalNote: ""
      },
      contactForm: {
        id: null,
        name: "",
        roleName: "",
        phone: "",
        priorityNo: 10,
        status: "active",
        description: ""
      }
    }
  },
  computed: {
    incidentLabIndex() {
      const idx = this.labOptions.findIndex((item) => Number(item.id || item.labId || 0) === Number(this.incidentForm.labId || 0))
      return idx >= 0 ? idx : 0
    },
    incidentLabText() {
      if (!Array.isArray(this.labOptions) || this.labOptions.length === 0) return "选择实验室"
      if (Number(this.incidentForm.labId || 0) <= 0) return "选择实验室"
      const current = this.labOptions[this.incidentLabIndex]
      return current ? (current.name || current.labName || "选择实验室") : "选择实验室"
    }
  },
  onShow() {
    if (!ensureAdmin()) {
      uni.showToast({ title: "无权限", icon: "none" })
      uni.reLaunch({ url: "/pages/login/login" })
      return
    }
    const s = uni.getStorageSync("session") || {}
    this.operator = s.username || ""
    this.loadAll()
  },
  methods: {
    resetDutyForm() {
      this.dutyForm = {
        id: null,
        dutyDate: "",
        shiftName: "",
        assigneeName: "",
        assigneePhone: "",
        backupName: "",
        backupPhone: "",
        status: "scheduled",
        note: ""
      }
    },
    resetIncidentForm() {
      this.incidentForm = {
        id: null,
        labId: 0,
        labName: "",
        title: "",
        incidentLevel: "medium",
        status: "reported",
        reporterName: "",
        reporterPhone: "",
        description: "",
        disposalNote: ""
      }
    },
    resetContactForm() {
      this.contactForm = {
        id: null,
        name: "",
        roleName: "",
        phone: "",
        priorityNo: 10,
        status: "active",
        description: ""
      }
    },
    onDutyDateChange(e) {
      this.dutyForm.dutyDate = (e && e.detail && e.detail.value) || ""
    },
    onIncidentLabChange(e) {
      const idx = Number((e && e.detail && e.detail.value) || 0)
      const row = this.labOptions[idx] || {}
      this.incidentForm.labId = Number(row.id || row.labId || 0)
      this.incidentForm.labName = String(row.name || row.labName || "").trim()
    },
    dutyStatusText(status) {
      const map = { scheduled: "待值班", on_duty: "值班中", completed: "已完成", closed: "已关闭" }
      return map[String(status || "").trim()] || (status || "-")
    },
    dutyTone(status) {
      if (status === "on_duty") return "status-info"
      if (status === "completed") return "status-success"
      if (status === "closed") return "status-muted"
      return "status-warning"
    },
    levelText(level) {
      const map = { low: "低", medium: "中", high: "高", critical: "严重" }
      return map[String(level || "").trim()] || (level || "-")
    },
    incidentStatusText(status) {
      const map = { reported: "已上报", processing: "处理中", closed: "已闭环" }
      return map[String(status || "").trim()] || (status || "-")
    },
    incidentTone(status) {
      if (status === "closed") return "status-muted"
      if (status === "processing") return "status-warning"
      return "status-danger"
    },
    async loadAll() {
      if (this.loading) return
      this.loading = true
      try {
        const [labsRes, dutyRes, incidentRes, contactRes] = await Promise.all([
          listLabs({ pageSize: 500 }),
          adminGetDutyRoster({}),
          adminGetIncidents({}),
          adminGetEmergencyContacts({})
        ])
        const labsPayload = (labsRes && labsRes.data) || {}
        const dutyPayload = (dutyRes && dutyRes.data) || {}
        const incidentPayload = (incidentRes && incidentRes.data) || {}
        const contactPayload = (contactRes && contactRes.data) || {}
        this.labOptions = Array.isArray(labsPayload.data)
          ? labsPayload.data.map((item) => ({
              ...item,
              id: Number(item.id || item.labId || 0),
              name: String(item.name || item.labName || "").trim()
            }))
          : []
        this.dutyRows = Array.isArray(dutyPayload.data) ? dutyPayload.data : []
        this.incidentRows = Array.isArray(incidentPayload.data) ? incidentPayload.data : []
        this.contactRows = sortByPriorityAsc(Array.isArray(contactPayload.data) ? contactPayload.data : [])
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" })
      } finally {
        this.loading = false
      }
    },
    async saveDuty() {
      if (!String(this.dutyForm.dutyDate || "").trim() || !String(this.dutyForm.shiftName || "").trim() || !String(this.dutyForm.assigneeName || "").trim()) {
        uni.showToast({ title: "请填写日期、班次和值班人", icon: "none" })
        return
      }
      this.savingDuty = true
      try {
        const res = await adminSaveDutyRoster({ ...this.dutyForm })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: "值班已保存", icon: "success" })
        this.resetDutyForm()
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.savingDuty = false
      }
    },
    editDuty(row) {
      this.activeTab = "duty"
      this.dutyForm = {
        id: row.id || null,
        dutyDate: row.dutyDate || "",
        shiftName: row.shiftName || "",
        assigneeName: row.assigneeName || "",
        assigneePhone: row.assigneePhone || "",
        backupName: row.backupName || "",
        backupPhone: row.backupPhone || "",
        status: row.status || "scheduled",
        note: row.note || ""
      }
    },
    async quickDutyStatus(row, status) {
      try {
        const res = await adminUpdateDutyRosterStatus(row.id, { status, note: row.note || "" })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "状态更新失败", icon: "none" })
          return
        }
        uni.showToast({ title: "状态已更新", icon: "success" })
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "状态更新失败", icon: "none" })
      }
    },
    async saveIncidentRecord() {
      if (!String(this.incidentForm.title || "").trim()) {
        uni.showToast({ title: "请填写事故标题", icon: "none" })
        return
      }
      this.savingIncident = true
      try {
        const res = await adminSaveIncident({ ...this.incidentForm })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: "事故已保存", icon: "success" })
        this.resetIncidentForm()
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.savingIncident = false
      }
    },
    editIncident(row) {
      this.activeTab = "incident"
      this.incidentForm = {
        id: row.id || null,
        labId: Number(row.labId || 0),
        labName: row.labName || "",
        title: row.title || "",
        incidentLevel: row.incidentLevel || "medium",
        status: row.status || "reported",
        reporterName: row.reporterName || "",
        reporterPhone: row.reporterPhone || "",
        description: row.description || "",
        disposalNote: row.disposalNote || ""
      }
    },
    async quickIncidentStatus(row, status) {
      const disposalNote = status === "closed"
        ? `${String(row.disposalNote || "").trim()} ${new Date().toLocaleString()} 已闭环`.trim()
        : String(row.disposalNote || "").trim()
      try {
        const res = await adminUpdateIncidentStatus(row.id, { status, disposalNote })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "状态更新失败", icon: "none" })
          return
        }
        uni.showToast({ title: "状态已更新", icon: "success" })
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "状态更新失败", icon: "none" })
      }
    },
    async saveContactRecord() {
      if (!String(this.contactForm.name || "").trim() || !String(this.contactForm.phone || "").trim()) {
        uni.showToast({ title: "请填写联系人和电话", icon: "none" })
        return
      }
      this.savingContact = true
      try {
        const res = await adminSaveEmergencyContact({ ...this.contactForm })
        const payload = (res && res.data) || {}
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" })
          return
        }
        uni.showToast({ title: "联系人已保存", icon: "success" })
        this.resetContactForm()
        this.loadAll()
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" })
      } finally {
        this.savingContact = false
      }
    },
    editContact(row) {
      this.activeTab = "contacts"
      this.contactForm = {
        id: row.id || null,
        name: row.name || "",
        roleName: row.roleName || "",
        phone: row.phone || "",
        priorityNo: Number(row.priorityNo || 10),
        status: row.status || "active",
        description: row.description || ""
      }
    },
    deleteContactRecord(row) {
      uni.showModal({
        title: "删除联系人",
        content: `确认删除 ${row.name || "该联系人"} 吗？`,
        success: async (modalRes) => {
          if (!modalRes.confirm) return
          try {
            const res = await adminDeleteEmergencyContact(row.id)
            const payload = (res && res.data) || {}
            if (!payload.ok) {
              uni.showToast({ title: payload.msg || "删除失败", icon: "none" })
              return
            }
            uni.showToast({ title: "已删除", icon: "success" })
            this.loadAll()
          } catch (e) {
            uni.showToast({ title: "删除失败", icon: "none" })
          }
        }
      })
    },
    callContact(phone) {
      const mobile = String(phone || "").trim()
      if (!mobile) {
        uni.showToast({ title: "电话为空", icon: "none" })
        return
      }
      uni.makePhoneCall({ phoneNumber: mobile })
    }
  }
}
</script>

<style lang="scss">
.dutyPage {
  padding-bottom: 24px;
}

.heroCard {
  border: 1px solid rgba(239, 68, 68, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #fff4f4 100%);
}

.heroTop,
.sectionHeader {
  align-items: flex-start;
}

.heroMeta {
  margin-top: 6px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.tabRow {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tabChip {
  min-width: 82px;
  height: 34px;
  line-height: 34px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #fff;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.tabChipOn {
  border-color: rgba(239, 68, 68, 0.26);
  background: #fff1f2;
  color: #b91c1c;
}

.sectionCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.mt8 {
  margin-top: 8px;
}

.field {
  flex: 1;
}

.pickerLike {
  min-height: 36px;
  border: 1px solid #d0d8e2;
  border-radius: 8px;
  padding: 8px 10px;
  box-sizing: border-box;
  font-size: 13px;
  color: #0f172a;
  background: #fff;
}

.chipRow {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  height: 30px;
  line-height: 30px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  padding: 0 10px;
  font-size: 12px;
  color: #475569;
  background: #fff;
}

.chipOn {
  border-color: #fecaca;
  background: #fff1f2;
  color: #b91c1c;
}

.textareaBase {
  min-height: 88px;
}

.list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rowItem {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}

.rowTitle {
  font-size: 13px;
  line-height: 19px;
  font-weight: 700;
  color: #0f172a;
}

.rowMeta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.actionRow {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.statusTag {
  flex-shrink: 0;
  min-width: 62px;
  height: 22px;
  line-height: 22px;
  border-radius: 999px;
  text-align: center;
  font-size: 10px;
  font-weight: 600;
  padding: 0 8px;
  box-sizing: border-box;
}

.status-info {
  color: #1d4ed8;
  background: #dbeafe;
}

.status-success {
  color: #15803d;
  background: #dcfce7;
}

.status-warning {
  color: #b45309;
  background: #fef3c7;
}

.status-danger {
  color: #b91c1c;
  background: #fee2e2;
}

.status-muted {
  color: #475569;
  background: #e2e8f0;
}

.severityDot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.severityDot.level-low {
  background: #10b981;
}

.severityDot.level-medium {
  background: #f59e0b;
}

.severityDot.level-high {
  background: #f97316;
}

.severityDot.level-critical {
  background: #ef4444;
}

.empty {
  font-size: 12px;
  color: #94a3b8;
}
</style>
