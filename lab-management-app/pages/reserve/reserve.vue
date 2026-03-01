<template>
  <view class="container reservePage">
    <view class="stack">
      <view class="card heroCard">
        <view class="rowBetween heroTop">
          <view>
            <view class="title">预约实验室</view>
            <view class="subtitle">选择实验室、日期与时段后提交审批</view>
          </view>
          <view class="statusTag info">{{ form.user || '未登录' }}</view>
        </view>
      </view>

      <view class="card formCard">
        <view class="label">实验室</view>
        <picker :range="labs" range-key="name" @change="onLabChange">
          <view class="valueBox">{{ labName }}</view>
        </picker>
        <view class="fieldError" v-if="errors.labName">{{ errors.labName }}</view>

        <view class="label">预约人（当前登录账号）</view>
        <input class="inputBase" v-model="form.user" disabled />

        <view class="label">日期</view>
        <picker mode="date" :value="form.date" :start="rules.minDate" :end="rules.maxDate" @change="onDateChange">
          <view class="calendarBtn">点击选择日期</view>
        </picker>
        <view class="fieldError" v-if="errors.date">{{ errors.date }}</view>
        <view class="muted">可预约日期：{{ rules.minDate || '-' }} 至 {{ rules.maxDate || '-' }}</view>
        <view class="muted" v-if="form.date">已选日期：{{ form.date }}</view>

        <view class="label">时间段</view>
        <view class="timePickerRow">
          <button class="btnSecondary miniBtn" size="mini" @click="openTimePicker">选择时间段</button>
          <view class="muted" v-if="form.time.length === 0">未选择</view>
          <view class="muted" v-else>已选 {{ form.time.length }} 段</view>
        </view>
        <view class="slotPreview" v-if="form.time.length > 0">
          <view class="chip" v-for="t in form.time" :key="t">{{ t }}</view>
        </view>
        <view class="fieldError" v-if="errors.time">{{ errors.time }}</view>
        <view class="muted">可预约时段：{{ rules.minTime || '-' }} - {{ rules.maxTime || '-' }}</view>

        <view class="label">用途说明（选填）</view>
        <textarea class="textareaBase" v-model="form.reason" placeholder="例如：数据结构实验教学" maxlength="255" />
        <view class="muted">{{ (form.reason || '').length }} / 255</view>
        <view class="fieldError" v-if="errors.reason">{{ errors.reason }}</view>
      </view>

      <view class="card summaryCard">
        <view class="cardTitle">提交前确认</view>
        <view class="summaryLine">实验室：{{ labName }}</view>
        <view class="summaryLine">日期：{{ form.date || '-' }}</view>
        <view class="summaryLine">时段：{{ selectedTimeText }}</view>
        <view class="summaryLine">用途：{{ form.reason || '未填写' }}</view>
        <button class="btnPrimary submitBtn" @click="submit">提交预约</button>
      </view>
    </view>

    <view v-if="showTimePicker" class="modalMask" @click="confirmTimePicker">
      <view class="modalCard stack" @click.stop>
        <view class="modalTitle">选择时间段（可多选）</view>

        <view class="sectionTitle">上午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsMorning"
            :key="t"
            class="slot"
            :class="{ selected: tempTimes.includes(t) }"
            @click="toggleTime(t)"
          >
            {{ t }}
          </view>
        </view>

        <view class="sectionTitle">下午</view>
        <view class="slots">
          <view
            v-for="t in timeSlotsAfternoon"
            :key="t"
            class="slot"
            :class="{ selected: tempTimes.includes(t) }"
            @click="toggleTime(t)"
          >
            {{ t }}
          </view>
        </view>

        <view class="modalActions">
          <button size="mini" class="btnSecondary miniBtn" @click="closeTimePicker">取消</button>
          <button size="mini" class="btnPrimary miniBtn" @click="confirmTimePicker">确定</button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { BASE_URL } from "@/common/api.js"

export default {
  data() {
    return {
      labName: "未选择",
      labs: [],
      form: { user: "", date: "", time: [], reason: "" },
      timeSlotsMorning: ["8:00-8:40", "8:45-9:35", "10:25-11:05", "11:10-11:50"],
      timeSlotsAfternoon: ["2:30-3:10", "3:15-3:55", "4:05-4:45", "4:50-5:30"],
      showTimePicker: false,
      tempTimes: [],
      errors: {
        labName: "",
        date: "",
        time: "",
        reason: ""
      },
      rules: {
        minDate: "",
        maxDate: "",
        minDaysAhead: 0,
        maxDaysAhead: 30,
        minTime: "08:00",
        maxTime: "22:00"
      }
    }
  },
  computed: {
    selectedTimeText() {
      if (this.form.time.length === 0) return "未选择"
      return this.form.time.join("，")
    }
  },
  onLoad(options) {
    if (options.labName) this.labName = decodeURIComponent(options.labName)
    this.syncCurrentUser()
    this.fetchReservationRules()
    this.fetchLabs()
  },
  onShow() {
    this.syncCurrentUser()
  },
  methods: {
    syncCurrentUser() {
      const s = uni.getStorageSync("session")
      const user = s && s.username ? s.username : ""
      this.form.user = user
      return user
    },
    fetchLabs() {
      uni.request({
        url: `${BASE_URL}/labs`,
        method: "GET",
        success: (res) => {
          this.labs = Array.isArray(res.data) ? res.data : []
          if (this.labName === "未选择" && this.labs.length > 0) {
            this.labName = this.labs[0].name || "未选择"
          }
          if (this.labName !== "未选择") {
            const exists = this.labs.find((l) => l.name === this.labName)
            if (!exists) this.labName = "未选择"
          }
        },
        fail: () => {
          uni.showToast({ title: "无法获取实验室", icon: "none" })
          this.labs = []
        }
      })
    },
    fetchReservationRules() {
      uni.request({
        url: `${BASE_URL}/reservation-rules`,
        method: "GET",
        success: (res) => {
          const payload = res.data || {}
          if (!payload.ok || !payload.data) return
          const data = payload.data
          this.rules.minDate = data.minDate || ""
          this.rules.maxDate = data.maxDate || ""
          this.rules.minDaysAhead = Number(data.minDaysAhead || 0)
          this.rules.maxDaysAhead = Number(data.maxDaysAhead || 30)
          this.rules.minTime = data.minTime || "08:00"
          this.rules.maxTime = data.maxTime || "22:00"
        }
      })
    },
    onLabChange(e) {
      const idx = Number(e.detail.value)
      const lab = this.labs[idx]
      this.labName = lab ? lab.name : "未选择"
      this.errors.labName = ""
    },
    onDateChange(e) {
      this.form.date = e.detail.value
      this.errors.date = ""
    },
    openTimePicker() {
      this.tempTimes = [...this.form.time]
      this.showTimePicker = true
    },
    closeTimePicker() {
      this.tempTimes = [...this.form.time]
      this.showTimePicker = false
    },
    toggleTime(time) {
      const idx = this.tempTimes.indexOf(time)
      if (idx >= 0) this.tempTimes.splice(idx, 1)
      else this.tempTimes.push(time)
    },
    confirmTimePicker() {
      this.form.time = [...this.tempTimes]
      this.showTimePicker = false
      this.errors.time = ""
    },
    validateForm() {
      this.errors.labName = ""
      this.errors.date = ""
      this.errors.time = ""
      this.errors.reason = ""
      let ok = true

      if (this.labName === "未选择") {
        this.errors.labName = "请选择实验室"
        ok = false
      }

      if (!this.form.date) {
        this.errors.date = "请选择预约日期"
        ok = false
      } else if (this.rules.minDate && this.form.date < this.rules.minDate) {
        this.errors.date = "日期早于可预约范围"
        ok = false
      } else if (this.rules.maxDate && this.form.date > this.rules.maxDate) {
        this.errors.date = "日期晚于可预约范围"
        ok = false
      }

      if (this.form.time.length === 0) {
        this.errors.time = "请至少选择一个时间段"
        ok = false
      }

      if ((this.form.reason || "").length > 255) {
        this.errors.reason = "用途说明不能超过 255 字"
        ok = false
      }

      return ok
    },
    submit() {
      const user = this.syncCurrentUser()
      if (!user) {
        uni.showToast({ title: "请先登录", icon: "none" })
        uni.reLaunch({ url: "/pages/login/login" })
        return
      }

      if (!this.validateForm()) return

      uni.showModal({
        title: "确认提交预约",
        content: `实验室：${this.labName}\n日期：${this.form.date}\n时间：${this.form.time.join(', ')}`,
        success: (m) => {
          if (!m.confirm) return
          uni.request({
            url: `${BASE_URL}/reservations`,
            method: "POST",
            header: { "Content-Type": "application/json" },
            data: {
              labName: this.labName,
              user,
              date: this.form.date,
              time: this.form.time.join(","),
              reason: this.form.reason
            },
            success: (res) => {
              if (!res.data || !res.data.ok) {
                const msg = (res.data && res.data.msg) || "提交失败"
                if (msg.includes("date")) this.errors.date = msg
                else if (msg.includes("time")) this.errors.time = msg
                else if (msg.includes("lab")) this.errors.labName = msg
                else uni.showToast({ title: msg, icon: "none" })
                return
              }

              const orderId = res.data.data && res.data.data.id ? res.data.data.id : "-"
              uni.showModal({
                title: "提交成功",
                content: `已提交预约申请，等待审批\n编号：${orderId}`,
                showCancel: false,
                success: () => {
                  uni.navigateBack()
                }
              })
            },
            fail: () => {
              uni.showToast({ title: "后端连接失败", icon: "none" })
            }
          })
        }
      })
    }
  }
}
</script>

<style lang="scss">
.reservePage {
  padding-bottom: 20px;
}

.heroCard {
  border: 1px solid rgba(22, 119, 255, 0.18);
  background: linear-gradient(160deg, #ffffff 0%, #f2f7ff 100%);
}

.heroTop {
  align-items: flex-start;
}

.formCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.valueBox {
  font-weight: 600;
  padding: 10px 12px;
  background: #f8fbff;
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  color: #0f172a;
}

.timePickerRow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.slotPreview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 4px;
}

.summaryCard {
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.summaryLine {
  margin-top: 8px;
  font-size: 12px;
  color: #475569;
}

.submitBtn {
  width: 100%;
  margin-top: 12px;
}

.miniBtn {
  min-height: 30px;
  line-height: 30px;
  padding: 0 10px;
  font-size: 12px;
  border-radius: 9px;
}

.textareaBase {
  min-height: 90px;
  width: 100%;
  box-sizing: border-box;
}

.slots {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.slot {
  padding: 8px 10px;
  border-radius: 999px;
  border: 1px solid #dbe3ef;
  background: #f8fafc;
  font-size: 12px;
  color: #334155;
}

.selected {
  border-color: #bfdbfe;
  background: #eaf3ff;
  color: #1d4ed8;
}
</style>
