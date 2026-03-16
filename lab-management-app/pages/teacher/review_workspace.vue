<template>
  <view class="container reviewWorkspacePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween">
          <view>
            <view class="title">Rubric 评阅台</view>
            <view class="subtitle">{{ submission.taskTitle || "作业评阅" }} ｜ {{ submission.studentDisplayName || submission.studentUserName || "-" }}</view>
          </view>
          <view class="actions">
            <button class="btnSecondary miniBtn" size="mini" :loading="loading" @click="loadWorkspace">刷新</button>
            <button class="btnGhost miniBtn" size="mini" @click="applyAi">AI 一键采纳</button>
          </view>
        </view>
        <view class="meta">文件：{{ submission.fileName || "-" }}</view>
        <view class="meta">当前状态：{{ submission.reviewStatus || "pending" }}</view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">Rubric 模板</view>
          <button class="btnSecondary miniBtn" size="mini" @click="addRubricItem">新增评分项</button>
        </view>
        <input class="inputBase" v-model.trim="rubricForm.title" maxlength="80" placeholder="评分模板标题" />
        <textarea class="textareaBase" v-model.trim="rubricForm.description" maxlength="300" placeholder="评分模板说明" />
        <view class="rubricList">
          <view class="rubricItem" v-for="(item, idx) in rubricForm.items" :key="`${idx}-${item.localKey}`">
            <view class="rowBetween">
              <view class="rubricIndex">评分项 {{ idx + 1 }}</view>
              <button class="btnDanger miniBtn" size="mini" @click="removeRubricItem(idx)">删除</button>
            </view>
            <input class="inputBase" v-model.trim="item.itemTitle" maxlength="80" placeholder="评分项名称" />
            <textarea class="textareaBase" v-model.trim="item.description" maxlength="200" placeholder="评分项说明" />
            <input class="inputBase" type="digit" v-model="item.maxScore" placeholder="满分值" />
          </view>
        </view>
        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" @click="saveRubric">保存 Rubric</button>
        </view>
      </view>

      <view class="card">
        <view class="rowBetween">
          <view class="cardTitle">本次批注</view>
          <button class="btnSecondary miniBtn" size="mini" @click="addAnnotation">新增批注</button>
        </view>
        <view class="annotationList">
          <view class="annotationItem" v-for="(item, idx) in annotations" :key="`${idx}-${item.localKey}`">
            <view class="rowBetween">
              <view class="rubricIndex">批注 {{ idx + 1 }}</view>
              <button class="btnDanger miniBtn" size="mini" @click="removeAnnotation(idx)">删除</button>
            </view>
            <view class="grid2">
              <input class="inputBase" v-model.trim="item.anchorType" maxlength="16" placeholder="定位类型，例如 file/page" />
              <input class="inputBase" v-model.trim="item.anchorKey" maxlength="32" placeholder="定位键，例如 page-1" />
            </view>
            <textarea class="textareaBase" v-model.trim="item.content" maxlength="300" placeholder="批注内容" />
          </view>
        </view>
      </view>

      <view class="card">
        <view class="cardTitle">评分提交</view>
        <view class="scoreList">
          <view class="scoreItem" v-for="(item, idx) in rubricScores" :key="`${idx}-${item.itemId || idx}`">
            <view class="scoreTitle">{{ item.itemTitle || `评分项 ${idx + 1}` }}</view>
            <view class="grid2">
              <input class="inputBase" type="digit" v-model="item.score" :placeholder="`满分 ${item.maxScore || 0}`" />
              <input class="inputBase" v-model.trim="item.comment" maxlength="160" placeholder="该项评语" />
            </view>
          </view>
        </view>
        <view class="grid2">
          <input class="inputBase" type="digit" v-model="reviewForm.reviewScore" placeholder="总分" />
          <picker mode="selector" :range="reviewStatusOptions" range-key="label" @change="onStatusChange">
            <view class="pickerField">{{ selectedStatusLabel }}</view>
          </picker>
        </view>
        <textarea class="textareaBase" v-model.trim="reviewForm.reviewNote" maxlength="255" placeholder="总体评语" />
        <view class="actions">
          <button class="btnPrimary miniBtn" size="mini" :loading="submitting" @click="submitReview">提交评阅</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import {
  teacherApplyAiReviewSuggestion,
  teacherGetReviewWorkspace,
  teacherReviewTaskStudentFile,
  teacherSaveTaskRubric
} from "@/common/api.js";

function newRubricItem() {
  return {
    localKey: `${Date.now()}-${Math.random()}`,
    itemTitle: "",
    description: "",
    maxScore: ""
  };
}

function newAnnotationItem() {
  return {
    localKey: `${Date.now()}-${Math.random()}`,
    annotationType: "comment",
    anchorType: "file",
    anchorKey: "",
    content: ""
  };
}

export default {
  data() {
    return {
      fileId: 0,
      taskId: 0,
      loading: false,
      submitting: false,
      submission: {},
      rubricForm: {
        title: "实验任务评分标准",
        description: "",
        items: [newRubricItem()]
      },
      rubricScores: [],
      annotations: [],
      reviewForm: {
        reviewStatus: "approved",
        reviewScore: "",
        reviewNote: ""
      },
      reviewStatusOptions: [
        { label: "通过", value: "approved" },
        { label: "驳回", value: "rejected" }
      ]
    };
  },
  computed: {
    selectedStatusLabel() {
      const hit = this.reviewStatusOptions.find((item) => item.value === this.reviewForm.reviewStatus);
      return hit ? hit.label : "选择状态";
    }
  },
  onLoad(options) {
    const fileId = Number((options && options.fileId) || 0);
    this.fileId = Number.isFinite(fileId) ? fileId : 0;
  },
  onShow() {
    this.loadWorkspace();
  },
  methods: {
    async loadWorkspace() {
      if (!this.fileId || this.loading) return;
      this.loading = true;
      try {
        const res = await teacherGetReviewWorkspace(this.fileId);
        const payload = (res && res.data) || {};
        if (!payload.ok || !payload.data) {
          uni.showToast({ title: payload.msg || "加载失败", icon: "none" });
          return;
        }
        const data = payload.data || {};
        this.submission = data.submission || {};
        this.taskId = Number((this.submission && this.submission.taskId) || 0);
        const rubric = data.rubric || {};
        const reviewExtras = data.reviewExtras || {};
        const rubricItems = Array.isArray(rubric.items) && rubric.items.length > 0
          ? rubric.items.map((item) => ({
              localKey: `${item.id || Math.random()}`,
              itemId: item.id,
              itemTitle: item.itemTitle || "",
              description: item.description || "",
              maxScore: item.maxScore == null ? "" : String(item.maxScore)
            }))
          : [newRubricItem()];
        this.rubricForm = {
          title: (rubric.template && rubric.template.title) || "实验任务评分标准",
          description: (rubric.template && rubric.template.description) || "",
          items: rubricItems
        };
        const scoreRows = Array.isArray(reviewExtras.rubricScores) ? reviewExtras.rubricScores : [];
        this.rubricScores = rubricItems.map((item) => {
          const hit = scoreRows.find((row) => Number(row.itemId || 0) === Number(item.itemId || 0));
          return {
            itemId: item.itemId || 0,
            itemTitle: item.itemTitle || "",
            maxScore: item.maxScore || "",
            score: hit && hit.score != null ? String(hit.score) : "",
            comment: (hit && hit.comment) || ""
          };
        });
        this.annotations = Array.isArray(reviewExtras.annotations) && reviewExtras.annotations.length > 0
          ? reviewExtras.annotations.map((item) => ({
              localKey: `${item.id || Math.random()}`,
              annotationType: item.annotationType || "comment",
              anchorType: item.anchorType || "file",
              anchorKey: item.anchorKey || "",
              content: item.content || ""
            }))
          : [];
        this.reviewForm.reviewStatus = this.submission.reviewStatus || "approved";
        this.reviewForm.reviewScore = this.submission.reviewScore == null ? "" : String(this.submission.reviewScore);
        this.reviewForm.reviewNote = this.submission.reviewNote || "";
      } catch (e) {
        uni.showToast({ title: "加载失败", icon: "none" });
      } finally {
        this.loading = false;
      }
    },
    onStatusChange(e) {
      const index = Number(e && e.detail && e.detail.value);
      const option = this.reviewStatusOptions[index];
      this.reviewForm.reviewStatus = option ? option.value : "approved";
    },
    addRubricItem() {
      this.rubricForm.items.push(newRubricItem());
    },
    removeRubricItem(index) {
      this.rubricForm.items.splice(index, 1);
      if (this.rubricForm.items.length === 0) this.rubricForm.items.push(newRubricItem());
    },
    addAnnotation() {
      this.annotations.push(newAnnotationItem());
    },
    removeAnnotation(index) {
      this.annotations.splice(index, 1);
    },
    async saveRubric() {
      if (!this.taskId) return;
      const items = this.rubricForm.items
        .map((item) => ({
          itemTitle: String(item.itemTitle || "").trim(),
          description: String(item.description || "").trim(),
          maxScore: Number(item.maxScore || 0)
        }))
        .filter((item) => item.itemTitle);
      const res = await teacherSaveTaskRubric(this.taskId, {
        title: this.rubricForm.title,
        description: this.rubricForm.description,
        items
      });
      const payload = (res && res.data) || {};
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "保存失败", icon: "none" });
        return;
      }
      uni.showToast({ title: "Rubric 已保存", icon: "success" });
      await this.loadWorkspace();
    },
    buildReviewPayload() {
      return {
        reviewStatus: this.reviewForm.reviewStatus,
        reviewScore: this.reviewForm.reviewScore === "" ? undefined : Number(this.reviewForm.reviewScore),
        reviewNote: this.reviewForm.reviewNote,
        rubricScores: this.rubricScores
          .filter((item) => Number(item.itemId || 0) > 0)
          .map((item) => ({
            itemId: Number(item.itemId || 0),
            score: item.score === "" ? undefined : Number(item.score),
            comment: item.comment
          })),
        annotations: this.annotations
          .filter((item) => String(item.content || "").trim())
          .map((item) => ({
            annotationType: item.annotationType,
            anchorType: item.anchorType,
            anchorKey: item.anchorKey,
            content: item.content
          }))
      };
    },
    async submitReview() {
      if (!this.fileId || this.submitting) return;
      this.submitting = true;
      try {
        const res = await teacherReviewTaskStudentFile(this.fileId, this.buildReviewPayload());
        const payload = (res && res.data) || {};
        if (!payload.ok) {
          uni.showToast({ title: payload.msg || "提交失败", icon: "none" });
          return;
        }
        uni.showToast({ title: "评阅已提交", icon: "success" });
        this.loadWorkspace();
      } catch (e) {
        uni.showToast({ title: "提交失败", icon: "none" });
      } finally {
        this.submitting = false;
      }
    },
    async applyAi() {
      const res = await teacherApplyAiReviewSuggestion(this.fileId);
      const payload = (res && res.data) || {};
      if (!payload.ok) {
        uni.showToast({ title: payload.msg || "AI 采纳失败", icon: "none" });
        return;
      }
      uni.showToast({ title: "AI 建议已执行", icon: "success" });
      this.loadWorkspace();
    }
  }
};
</script>

<style lang="scss">
.reviewWorkspacePage {
  padding-bottom: 24px;
}

.heroCard,
.rubricItem,
.annotationItem,
.scoreItem {
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.rubricList,
.annotationList,
.scoreList {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rubricItem,
.annotationItem,
.scoreItem {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
}

.rubricIndex,
.scoreTitle {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.grid2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
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
