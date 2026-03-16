<template>
  <view class="container priorityPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">预约候补与优先级</view>
            <view class="subtitle">权重配置、规则预演、候补队列递补</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadAll">刷新</button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">优先级权重</view>
          <button class="btnPrimary miniBtn" size="mini" :loading="saving" @click="saveRule">保存</button>
        </view>
        <view class="grid2">
          <input class="inputBase" v-model.number="rule.teacherWeight" type="number" placeholder="教师权重" />
          <input class="inputBase" v-model.number="rule.studentWeight" type="number" placeholder="学生权重" />
          <input class="inputBase" v-model.number="rule.adminWeight" type="number" placeholder="管理员权重" />
          <input class="inputBase" v-model.number="rule.defaultWeight" type="number" placeholder="默认用途权重" />
          <input class="inputBase" v-model.number="rule.teachingWeight" type="number" placeholder="教学用途权重" />
          <input class="inputBase" v-model.number="rule.researchWeight" type="number" placeholder="科研用途权重" />
          <input class="inputBase" v-model.number="rule.violationPenalty" type="number" placeholder="违约扣分" />
          <input class="inputBase" v-model.number="rule.waitHourBonusCap" type="number" placeholder="等待加分上限小时" />
        </view>
        <input class="inputBase" v-model.number="rule.waitHourBonus" type="digit" placeholder="每小时等待加分" />
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">规则预演</view>
          <button class="btnSecondary miniBtn" size="mini" :loading="previewing" @click="previewRule">预演</button>
        </view>
        <view class="grid2">
          <input class="inputBase" v-model.trim="previewForm.labName" placeholder="实验室名称" />
          <input class="inputBase" v-model.trim="previewForm.date" placeholder="日期 YYYY-MM-DD" />
        </view>
        <input class="inputBase" v-model.trim="previewForm.time" placeholder="时间段，例如 08:00-08:40" />
        <view class="previewList" v-if="previewItems.length > 0">
          <view class="previewItem" v-for="item in previewItems" :key="item.id">
            <view class="rowBetween">
              <view class="previewTitle">{{ item.userName }}</view>
              <view class="statusTag info">{{ item.priorityScore }}</view>
            </view>
            <view class="meta">角色：{{ item.userRole || "-" }} ｜ 原因：{{ item.reason || "-" }}</view>
            <view class="meta muted">创建：{{ item.createdAt || "-" }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">候补队列</view>
          <view class="muted">按优先级排序</view>
        </view>
        <view class="emptyText muted" v-if="waitlist.length === 0">当前没有候补记录</view>
        <view class="waitlistList" v-else>
          <view class="waitlistItem" v-for="item in waitlist" :key="item.id">
            <view class="rowBetween">
              <view class="previewTitle">{{ item.labName }} {{ item.date }} {{ item.time }}</view>
              <view class="statusTag" :class="item.status === 'waiting' ? 'warning' : 'success'">{{ item.status }}</view>
            </view>
            <view class="meta">申请人：{{ item.userName }}（{{ item.userRole || "-" }}）</view>
            <view class="meta">优先分：{{ item.priorityScore }} ｜ 原因：{{ item.reason || "-" }}</view>
            <view class="meta muted">创建：{{ item.createdAt || "-" }}</view>
            <view class="actions">
              <button v-if="item.status === 'waiting'" class="btnPrimary miniBtn" size="mini" @click="promote(item)">手动递补</button>
              <button v-if="item.status === 'waiting'" class="btnDanger miniBtn" size="mini" @click="cancelWaitlist(item)">取消候补</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  adminGetReservationPriorityRules,
  adminPreviewReservationPriority,
  adminPromoteReservationWaitlist,
  adminSaveReservationPriorityRules,
  cancelReservationWaitlist,
  listReservationWaitlist
} from "@/common/api.js";

export default {
  data() {
    return {
      loading: false,
      saving: false,
      previewing: false,
      rule: {
        teacherWeight: 30,
        studentWeight: 10,
        adminWeight: 20,
        teachingWeight: 25,
        researchWeight: 15,
        defaultWeight: 5,
        violationPenalty: 15,
        waitHourBonus: 1,
        waitHourBonusCap: 48
      },
      previewForm: {
        labName: "",
        date: "",
        time: ""
      },
      previewItems: [],
      waitlist: []
    };
  },
  onShow() {
    this.loadAll();
  },
  methods: {
    async loadAll() {
      if (this.loading) return;
      this.loading = true;
      try {
        const [ruleRes, waitRes] = await Promise.all([
          adminGetReservationPriorityRules(),
          listReservationWaitlist({ mine: 0, status: "waiting" })
        ]);
        const rulePayload = (ruleRes && ruleRes.data) || {};
        const waitPayload = (waitRes && waitRes.data) || {};
        if (rulePayload.ok && rulePayload.data) {
          this.rule = { ...this.rule, ...(rulePayload.data || {}) };
        }
        this.waitlist = waitPayload.ok && Array.isArray(waitPayload.data) ? waitPayload.data : [];
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" });
      } finally {
        this.loading = false;
      }
    },
    async saveRule() {
      this.saving = true;
      try {
        const res = await adminSaveReservationPriorityRules(this.rule);
        const payload = (res && res.data) || {};
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "保存失败", icon: "none" });
          return;
        }
        uni.showToast({ title: "已保存", icon: "success" });
        this.rule = { ...this.rule, ...(payload.data || {}) };
      } catch (e) {
        uni.showToast({ title: "保存失败", icon: "none" });
      } finally {
        this.saving = false;
      }
    },
    async previewRule() {
      this.previewing = true;
      try {
        const res = await adminPreviewReservationPriority({
          ...this.previewForm,
          rule: this.rule
        });
        const payload = (res && res.data) || {};
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "预演失败", icon: "none" });
          return;
        }
        this.previewItems = payload.data && Array.isArray(payload.data.items) ? payload.data.items : [];
      } catch (e) {
        uni.showToast({ title: "预演失败", icon: "none" });
      } finally {
        this.previewing = false;
      }
    },
    async promote(item) {
      const res = await adminPromoteReservationWaitlist(item.id);
      const payload = (res && res.data) || {};
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "递补失败", icon: "none" });
        return;
      }
      uni.showToast({ title: "已递补", icon: "success" });
      this.loadAll();
    },
    async cancelWaitlist(item) {
      const res = await cancelReservationWaitlist(item.id);
      const payload = (res && res.data) || {};
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "取消失败", icon: "none" });
        return;
      }
      uni.showToast({ title: "已取消", icon: "success" });
      this.loadAll();
    }
  }
};
</script>

<style lang="scss">
.priorityPage {
  padding-bottom: 24px;
}

.heroCard,
.waitlistItem,
.previewItem {
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.inputBase {
  margin-top: 10px;
}

.previewList,
.waitlistList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.previewItem,
.waitlistItem {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
}

.previewTitle {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.meta,
.emptyText {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>
