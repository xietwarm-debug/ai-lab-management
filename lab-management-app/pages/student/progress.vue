<template>
  <view class="container progressPage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">进度中心</view>
            <view class="subtitle">作业、预约、借用、报修、签到统一追踪</view>
          </view>
          <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadData">刷新</button>
        </view>
      </view>

      <view class="summaryGrid">
        <view class="card summaryCard" v-for="item in summaryCards" :key="item.key">
          <view class="summaryLabel">{{ item.label }}</view>
          <view class="summaryValue">{{ item.value }}</view>
          <view class="summaryHint">{{ item.hint }}</view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">待处理</view>
          <view class="muted">最多展示 12 条</view>
        </view>
        <view class="emptyText muted" v-if="todoItems.length === 0">当前没有待处理事项</view>
        <view class="todoList" v-else>
          <view class="todoItem" v-for="(item, idx) in todoItems" :key="`${item.type}-${item.id || idx}`" @click="openItem(item)">
            <view class="rowBetween">
              <view class="todoTitle">{{ item.title || typeText(item.type) }}</view>
              <view class="statusTag" :class="toneByStatus(item.status)">{{ statusText(item.status) }}</view>
            </view>
            <view class="todoMeta">{{ item.courseName || item.labName || item.expectedReturnAt || item.date || "" }}</view>
            <view class="todoMeta muted">{{ item.deadline || item.startAt || item.createdAt || item.updatedAt || item.submittedAt || "-" }}</view>
          </view>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">最新时间线</view>
          <view class="muted">综合动态</view>
        </view>
        <view class="emptyText muted" v-if="timeline.length === 0">暂无动态</view>
        <view class="timelineList" v-else>
          <view class="timelineItem" v-for="(item, idx) in timeline" :key="`${item.type}-${item.id || idx}`" @click="openItem(item)">
            <view class="timelineDot"></view>
            <view class="timelineBody">
              <view class="rowBetween">
                <view class="timelineTitle">{{ item.title || typeText(item.type) }}</view>
                <view class="timelineType">{{ typeText(item.type) }}</view>
              </view>
              <view class="timelineMeta">{{ item.courseName || item.labName || item.time || item.expectedReturnAt || item.date || "" }}</view>
              <view class="timelineMeta muted">{{ item.updatedAt || item.reviewedAt || item.submittedAt || item.createdAt || item.finalCheckinAt || item.deadline || item.startAt || "-" }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { getStudentProgress } from "@/common/api.js";
import { requireRole } from "@/common/session.js";

export default {
  data() {
    return {
      loading: false,
      dataPack: {
        summary: {},
        todoItems: [],
        timeline: []
      }
    };
  },
  computed: {
    summaryCards() {
      const summary = this.dataPack.summary || {};
      return [
        { key: "task", label: "待提交作业", value: Number(summary.pendingTaskCount || 0), hint: "含逾期任务" },
        { key: "review", label: "待批改", value: Number(summary.pendingReviewCount || 0), hint: "已提交待教师评阅" },
        { key: "reserve", label: "活跃预约", value: Number(summary.activeReservationCount || 0), hint: "待审批 / 已通过" },
        { key: "waitlist", label: "候补队列", value: Number(summary.waitlistCount || 0), hint: "预约冲突后的排队" },
        { key: "borrow", label: "借用进行中", value: Number(summary.borrowActiveCount || 0), hint: `逾期 ${Number(summary.borrowOverdueCount || 0)}` },
        { key: "attendance", label: "待签到", value: Number(summary.pendingAttendanceCount || 0), hint: "当前开放的课堂签到" }
      ];
    },
    todoItems() {
      return Array.isArray(this.dataPack.todoItems) ? this.dataPack.todoItems : [];
    },
    timeline() {
      return Array.isArray(this.dataPack.timeline) ? this.dataPack.timeline : [];
    }
  },
  onShow() {
    const session = requireRole(["student"], { message: "仅学生可访问" });
    if (!session) return;
    this.loadData();
  },
  methods: {
    async loadData() {
      if (this.loading) return;
      this.loading = true;
      try {
        const res = await getStudentProgress();
        const payload = (res && res.data) || {};
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" });
          return;
        }
        this.dataPack = payload.data;
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" });
      } finally {
        this.loading = false;
      }
    },
    typeText(type) {
      const map = {
        task: "作业",
        reservation: "预约",
        waitlist: "候补",
        borrow: "借用",
        repair: "报修",
        attendance: "签到",
        attendance_history: "签到记录"
      };
      return map[type] || type || "动态";
    },
    statusText(status) {
      const map = {
        pending_submit: "待提交",
        overdue: "已逾期",
        pending_review: "待批改",
        reviewed_pass: "已通过",
        reviewed_reject: "已驳回",
        pending: "待处理",
        approved: "已通过",
        waiting: "排队中",
        present: "已完成",
        pending_confirm: "待确认",
        submitted: "已提交",
        accepted: "已受理",
        processing: "处理中"
      };
      return map[status] || status || "-";
    },
    toneByStatus(status) {
      if (["overdue", "reviewed_reject", "rejected"].includes(status)) return "danger";
      if (["approved", "present", "reviewed_pass"].includes(status)) return "success";
      return "warning";
    },
    openItem(item) {
      const path = String((item && item.actionPath) || "").trim();
      if (!path) return;
      uni.navigateTo({ url: path });
    }
  }
};
</script>

<style lang="scss">
.progressPage {
  padding-bottom: 24px;
}

.heroCard,
.summaryCard {
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.summaryGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summaryCard {
  min-height: 96px;
}

.summaryLabel {
  font-size: 12px;
  color: #64748b;
}

.summaryValue {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.summaryHint,
.todoMeta,
.timelineMeta,
.emptyText {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.todoList,
.timelineList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.todoItem {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
}

.todoTitle,
.timelineTitle {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.timelineItem {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.timelineDot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 999px;
  background: #2563eb;
  flex-shrink: 0;
}

.timelineBody {
  flex: 1;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.timelineType {
  font-size: 12px;
  color: #2563eb;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}
</style>
