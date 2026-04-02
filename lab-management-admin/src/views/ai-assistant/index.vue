<template>
  <div class="page-container ai-page">
    <section class="workspace-shell">
      <div class="workspace-main">
        <!-- 左侧：类 Gemini 对话主区 -->
        <article class="chat-panel">
          <!-- 顶部状态栏 -->
          <header class="chat-header">
            <div class="assistant-identity">
              <el-dropdown trigger="click" @command="handleHeaderCommand">
                <div class="assistant-title-row cursor-pointer">
                  <div class="ai-avatar-mini">
                    <img :src="assistantAvatar" alt="宁宁头像" />
                  </div>
                  <h2>宁宁 <span class="version-tag">管理后台助手 1.0</span></h2>
                  <el-icon class="ml-1 text-gray-400"><ArrowDown /></el-icon>
                </div>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="dailyBrief"><el-icon><Setting /></el-icon>今日 AI 简报</el-dropdown-item>
                    <el-dropdown-item command="riskAlerts"><el-icon><QuestionFilled /></el-icon>风险提醒</el-dropdown-item>
                    <el-dropdown-item command="equipmentHealth"><el-icon><QuestionFilled /></el-icon>设备预测</el-dropdown-item>
                    <el-dropdown-item command="refreshPrediction"><el-icon><Refresh /></el-icon>刷新设备预测</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <div class="header-actions">
              <el-button-group>
                <el-button text @click="loadHistory"><el-icon class="mr-1"><Refresh /></el-icon>记录</el-button>
                <el-button text :loading="pageLoading" @click="reloadAll">全量更新</el-button>
              </el-button-group>
              <div class="divider-v"></div>
              <el-popconfirm title="确认清空当前会话历史？" @confirm="handleClearHistory">
                <template #reference>
                  <el-button circle type="danger" plain size="small"><el-icon><Delete /></el-icon></el-button>
                </template>
              </el-popconfirm>
            </div>
          </header>

          <div class="assistant-shortcuts">
            <el-button
              v-for="item in adminShortcutActions"
              :key="item.key"
              text
              class="shortcut-chip"
              @click="runShortcutAction(item.key)"
            >
              {{ item.label }}
            </el-button>
          </div>

          <!-- 核心对话区 -->
          <div ref="chatBodyRef" class="chat-body">
            <!-- 欢迎引导 (增强版) -->
            <div v-if="messages.length === 0" class="welcome-container">
              <div class="welcome-card fade-in-up">
                <h1 class="gemini-greeting">
                  <span class="gradient-text">你好，我是宁宁</span>
                </h1>
                <p class="gemini-subtitle">
                  今天我能为您处理什么后台事务？<br/>
                  您可以让我 <span class="text-highlight">处理预约</span>、<span class="text-highlight">监测设备风险</span> 或 <span class="text-highlight">检索数据结论</span>。
                </p>
              </div>
              
              <!-- 快捷入口卡片 -->
              <div class="quick-grid fade-in-up-delay">
                <div v-for="prompt in quickPrompts" :key="prompt" class="quick-card-item" @click="usePrompt(prompt)">
                  <el-icon class="card-icon"><ChatLineRound /></el-icon>
                  <span class="card-text">{{ prompt }}</span>
                  <el-icon class="card-arrow"><TopRight /></el-icon>
                </div>
              </div>
            </div>

            <!-- 消息列表 -->
            <div v-else class="message-list">
              <div
                v-for="(item, index) in messages"
                :key="item.id"
                class="message-row"
                :class="`message-row--${item.role}`"
              >
                <!-- 助手头像 -->
                <div v-if="item.role === 'assistant'" class="message-avatar-wrap">
                  <div class="ai-avatar-inner">
                    <img :src="assistantAvatar" alt="宁宁头像" />
                  </div>
                </div>

                <div class="message-content" :class="`message-content--${item.role}`">
                  <div class="message-bubble" :class="`message-bubble--${item.role}`">
                    <p class="message-text">{{ item.text }}</p>

                    <div v-if="item.files && item.files.length" class="message-attached-files-list">
                      <div v-for="f in item.files" :key="f.id" class="attached-file-chip-bubble">
                        <el-icon><Document /></el-icon> <span>{{ f.originalName || f.original_name }}</span>
                      </div>
                    </div>

                    <!-- 联网信源 (增强 UI) -->
                    <div v-if="item.sources?.length" class="source-container">
                      <div class="source-tag-header">引用来源</div>
                      <div class="source-flex">
                        <a 
                          v-for="(source, index) in item.sources" 
                          :key="index"
                          :href="source.url" 
                          target="_blank" 
                          class="source-chip"
                        >
                          <span class="sc-idx">{{ index + 1 }}</span>
                          <span class="sc-title">{{ source.title || sourceHost(source.url) }}</span>
                        </a>
                      </div>
                    </div>

                    <!-- 确认导入资产卡片 -->
                    <div v-if="item.action === 'import_confirmation' && item.meta?.task_id" class="import-confirm-card">
                      <el-card shadow="hover">
                        <template #header>
                          <div class="import-header">
                            <span style="font-weight: 600;">📊 准备导入 {{ item.meta.total_count }} 条资产数据</span>
                          </div>
                        </template>
                        <el-table :data="item.meta.preview_data" size="small" style="width: 100%; margin-bottom: 12px; background: transparent;">
                          <el-table-column prop="asset_name" label="资产名称" />
                          <el-table-column prop="category" label="分类" />
                          <el-table-column prop="location" label="位置" />
                          <el-table-column prop="status" label="状态" />
                        </el-table>
                        <div style="color: #bbb; font-size: 12px; text-align: center; margin-bottom: 15px;">由于空间有限，仅展示部分预览</div>
                        <div style="display: flex; justify-content: flex-end; gap: 8px;">
                          <el-button type="primary" size="small" @click="confirmImportAction(item)" :loading="item.isImporting">
                            确认导入
                          </el-button>
                          <el-button size="small" @click="cancelImportAction(item)" :disabled="item.isImporting">取消</el-button>
                        </div>
                      </el-card>
                    </div>

                    <div class="message-tools">
                      <el-button
                        v-if="item.role === 'assistant' && item.helper"
                        link
                        size="small"
                        type="primary"
                        @click="openHelperPanel(item.helper)"
                      >
                        补充信息
                      </el-button>
                      <el-button link size="small" @click="copyMessage(item.text)">复制</el-button>
                      <el-button v-if="item.role === 'assistant'" link size="small" @click="regenerateMessage(index)">重答</el-button>
                    </div>
                  </div>
                  <div class="message-meta">{{ item.createdAt }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部悬浮输入区 (Gemini Composer 极致化) -->
          <footer class="composer-wrapper" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop">
            <div class="composer-inner" :class="{ 'is-focused': isComposerFocused, 'is-dragging': isDragging }">
              <div v-if="selectedFileIds.length > 0" class="selected-files-area">
                <div v-for="fileId in selectedFileIds" :key="fileId" class="selected-file-chip">
                  <el-icon><Document /></el-icon>
                  <span class="file-name" :title="getFileName(fileId)">{{ getFileName(fileId) }}</span>
                  <el-icon class="remove-icon" @click.stop="toggleFileSelection(fileId, false)"><Close /></el-icon>
                </div>
              </div>
              <el-input
                v-model="chatInput"
                class="composer-textarea"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 8 }"
                resize="none"
                placeholder="在此输入指令，例如：生成本周实验室设备报表..."
                @focus="isComposerFocused = true"
                @blur="isComposerFocused = false"
                @keyup.ctrl.enter="submitChat"
              />

              <div class="composer-footer">
                <div class="tools-left">
                  <el-button circle class="tool-btn" @click="submitWebSearch" title="联网搜索">
                    <el-icon><Search /></el-icon>
                  </el-button>
                  <el-button circle class="tool-btn" :loading="fileUploading" @click="triggerFileUpload" title="上传参考文件">
                    <el-icon><Paperclip /></el-icon>
                  </el-button>
                  <el-button circle class="tool-btn" @click="fileManagerVisible = true" title="文件知识库">
                    <el-badge :value="selectedFileIds.length" :hidden="selectedFileIds.length === 0" type="primary" :offset="[5, 5]">
                      <el-icon><FolderOpened /></el-icon>
                    </el-badge>
                  </el-button>
                  <el-button
                    circle
                    class="tool-btn"
                    :class="{ 'is-active': isRecording }"
                    :disabled="!speechSupported"
                    @click="toggleVoiceInput"
                    title="语音输入"
                  >
                    <el-icon><Microphone /></el-icon>
                  </el-button>
                  <input type="file" ref="fileInputRef" style="display: none" accept=".txt,.md,.csv,.docx,.xlsx,.pdf" @change="handleFileUpload" />
                </div>
                <div class="tools-right">
                  <el-button 
                    type="primary" 
                    class="send-pill"
                    :loading="chatLoading" 
                    :disabled="!chatInput.trim()"
                    @click="submitChat"
                  >
                    发送 <el-icon class="ml-1"><Position /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
            <div class="composer-hint">
              <span class="kbd">Ctrl</span> + <span class="kbd">Enter</span> 快速发送 | AI 可能会产生误差，请以实际系统数据为准
            </div>
            <div v-if="!speechSupported" class="composer-hint">当前浏览器不支持语音输入</div>
            <div v-else-if="isRecording" class="composer-hint">正在语音识别，点击麦克风结束并发送</div>
          </footer>

          <!-- 文件知识库抽屉 -->
          <el-drawer
            v-model="fileManagerVisible"
            direction="rtl"
            size="400px"
            title="助手文件与知识库"
            class="file-manager-drawer"
            @open="loadFiles"
          >
            <div class="file-manager-container" v-loading="fileManagerLoading">
              <div class="file-manager-desc">
                上传的文件可直接勾选作为当前会话参考，或加入全局知识库检索。支持 txt, md, csv, docx, xlsx, pdf。
              </div>

              <div class="file-list">
                <el-empty v-if="uploadedFiles.length === 0" description="暂无文件，请点击左下角别针图标上传" :image-size="60"></el-empty>
                <div v-for="file in uploadedFiles" :key="file.id" class="file-item">
                  <div class="file-item-left">
                    <el-checkbox
                      :model-value="selectedFileIds.includes(file.id)"
                      @change="(val) => toggleFileSelection(file.id, val)"
                    />
                    <el-icon class="file-icon"><Document /></el-icon>
                    <div class="file-info">
                      <div class="file-name" :title="file.originalName || file.original_name">{{ file.originalName || file.original_name }}</div>
                      <div class="file-meta">{{ file.createdAt || file.created_at }} | {{ file.fileSize ? (file.fileSize / 1024).toFixed(1) : (file.file_size / 1024).toFixed(1) }} KB</div>
                    </div>
                  </div>
                  <div class="file-item-right">
                    <el-tooltip content="是否加入全局知识库" placement="top">
                      <el-switch
                        v-model="file.inKnowledge"
                        :active-value="1"
                        :inactive-value="0"
                        size="small"
                        @change="() => handleToggleKnowledge(file)"
                      />
                    </el-tooltip>
                    <el-popconfirm title="确认删除此文件？" @confirm="handleDeleteFile(file.id)">
                      <template #reference>
                        <el-button type="danger" link size="small"><el-icon><Delete /></el-icon></el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </div>
          </el-drawer>

          <el-drawer
            v-model="helperPanelVisible"
            direction="rtl"
            size="420px"
            :with-header="false"
            class="pending-helper-drawer"
          >
            <div class="pending-helper-panel">
              <div class="pending-helper-header">
                <div>
                  <h3>{{ helperPanelTitle }}</h3>
                  <p>选择后发送给宁宁继续处理，不用手打完整描述。</p>
                </div>
                <el-button text @click="helperPanelVisible = false">收起</el-button>
              </div>

              <div v-if="activeHelper" class="pending-helper-summary">
                <div class="pending-helper-label">当前还缺</div>
                <div class="pending-helper-tags">
                  <el-tag v-for="slot in activeHelper.missingSlots" :key="slot" effect="plain" round>
                    {{ helperSlotLabel(slot) }}
                  </el-tag>
                </div>
              </div>

              <div v-if="activeHelperQuestions.length" class="pending-helper-section">
                <div class="pending-helper-label">助手提示</div>
                <div class="pending-helper-tips">
                  <div v-for="item in activeHelperQuestions" :key="item.key" class="pending-helper-tip">
                    {{ item.question }}
                  </div>
                </div>
              </div>

              <div v-if="showHelperPlans" class="pending-helper-section">
                <div class="pending-helper-label">可选方案</div>
                <div class="plan-option-list">
                  <button
                    v-for="plan in activeHelperPlans"
                    :key="plan.planId"
                    type="button"
                    class="plan-option-card"
                    :class="{ 'is-active': helperForm.selectedPlanId === plan.planId }"
                    @click="selectHelperPlan(plan)"
                  >
                    <div class="plan-option-top">
                      <strong>{{ plan.planId }}</strong>
                      <span>{{ plan.labName || '未命名实验室' }}</span>
                    </div>
                    <p>{{ plan.date || '-' }} {{ plan.time || '-' }}</p>
                    <p v-if="plan.reason">{{ plan.reason }}</p>
                  </button>
                </div>
              </div>

              <div v-if="shouldShowHelperField('labName')" class="pending-helper-section">
                <div class="pending-helper-label">实验室</div>
                <el-select
                  v-model="helperForm.labName"
                  filterable
                  clearable
                  placeholder="请选择实验室"
                  :loading="helperLabsLoading"
                  @visible-change="handleHelperLabSelectOpen"
                >
                  <el-option
                    v-for="item in helperLabOptions"
                    :key="item.id || item.name"
                    :label="item.name"
                    :value="item.name"
                  />
                </el-select>
              </div>

              <div v-if="shouldShowHelperField('date')" class="pending-helper-section">
                <div class="pending-helper-label">日期</div>
                <div class="pending-helper-chip-row">
                  <button
                    v-for="item in helperDateOptions"
                    :key="item.value"
                    type="button"
                    class="helper-chip"
                    :class="{ 'is-active': helperForm.date === item.value }"
                    @click="helperForm.date = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
                <el-date-picker
                  v-model="helperForm.date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  placeholder="选择具体日期"
                  class="pending-helper-date-picker"
                />
              </div>

              <div v-if="shouldShowHelperField('time')" class="pending-helper-section">
                <div class="pending-helper-label">时间段</div>
                <div class="pending-helper-chip-row">
                  <button
                    v-for="item in helperTimeOptions"
                    :key="item.value"
                    type="button"
                    class="helper-chip"
                    :class="{ 'is-active': helperForm.time === item.value }"
                    @click="helperForm.time = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div v-if="shouldShowHelperField('reason')" class="pending-helper-section">
                <div class="pending-helper-label">用途</div>
                <el-input v-model="helperForm.reason" type="textarea" :rows="3" placeholder="例如：课程实验、期末上机测试" />
              </div>

              <div v-if="shouldShowHelperField('description')" class="pending-helper-section">
                <div class="pending-helper-label">故障描述</div>
                <el-input v-model="helperForm.description" type="textarea" :rows="3" placeholder="例如：无法开机、蓝屏、断网" />
              </div>

              <div v-if="shouldShowHelperField('location')" class="pending-helper-section">
                <div class="pending-helper-label">报修位置</div>
                <el-input v-model="helperForm.location" placeholder="例如：A203 物联网实验室" />
              </div>

              <div v-if="shouldShowHelperField('equipmentHint')" class="pending-helper-section">
                <div class="pending-helper-label">设备编号</div>
                <el-input v-model="helperForm.equipmentHint" placeholder="例如：A203-HOST-001" />
              </div>

              <div class="pending-helper-footer">
                <el-button @click="helperPanelVisible = false">稍后再说</el-button>
                <el-button type="primary" :disabled="!canSubmitHelperForm" :loading="chatLoading" @click="submitHelperPanel">
                  发送补充信息
                </el-button>
              </div>
            </div>
          </el-drawer>
        </article>


      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Position, Search, ChatLineRound, ArrowDown,
  Refresh, Delete, Setting, QuestionFilled,
  TopRight, Microphone, Paperclip, FolderOpened,
  Document, Close
} from '@element-plus/icons-vue'
import {
  chatWithAgent,
  clearAgentHistory,
  getAdminAiDailyBrief,
  getAdminAiEquipmentHealth,
  getAdminAiRiskAlerts,
  getAgentHistory,
  queryAdminStatsAi,
  refreshAdminAiEquipmentHealth,
  uploadAgentFile,
  getAgentFiles,
  deleteAgentFile,
  toggleAgentFileKnowledge,
  executeAgentImport
} from '@/api/ai'
import { getLabs } from '@/api/labs'
import assistantAvatar from '@/static/ningning.png'

const chatBodyRef = ref(null)
const isComposerFocused = ref(false)
const pageLoading = ref(false)
const chatLoading = ref(false)
const speechSupported = ref(false)
const isRecording = ref(false)

const isDragging = ref(false)
const fileInputRef = ref(null)

function getFileName(id) {
  const f = uploadedFiles.value.find(x => x.id === id)
  if (f) return f.originalName || f.original_name || '文件'
  return '未命名文件'
}

function handleDrop(event) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    for (const file of files) {
      handleSingleFileUpload(file)
    }
  }
}

async function handleSingleFileUpload(file) {
  const validExts = ['.txt', '.md', '.csv', '.docx', '.xlsx', '.pdf']
  const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!validExts.includes(fileExt)) {
    ElMessage.warning('不支持的文件格式: ' + file.name)
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 20MB: ' + file.name)
    return
  }
  const formData = new FormData()
  formData.append('file', file)
  fileUploading.value = true
  try {
    const response = await uploadAgentFile(formData)
    const newFile = response?.data?.data
    if (newFile && newFile.id) {
      ElMessage.success('文件上传成功')
      if (!selectedFileIds.value.includes(newFile.id)) {
        selectedFileIds.value.push(newFile.id)
      }
      await loadFiles()
    }
  } catch (error) {
    const msg = error?.response?.data?.msg || '上传失败'
    ElMessage.error(msg)
  } finally {
    fileUploading.value = false
  }
}

const fileUploading = ref(false)
const fileManagerVisible = ref(false)
const fileManagerLoading = ref(false)
const uploadedFiles = ref([])
const selectedFileIds = ref([])

const messages = ref([])
const chatInput = ref('')
const recognizedSpeech = ref('')
const helperPanelVisible = ref(false)
const helperLabsLoading = ref(false)
const helperLabOptions = ref([])
const activeHelper = ref(null)
const helperDateOptions = ref([])

let speechRecognizer = null
let shouldSendVoiceResult = false

const helperTimeOptions = [
  { value: '08:00-08:40', label: '第1节 08:00-08:40' },
  { value: '08:45-09:35', label: '第2节 08:45-09:35' },
  { value: '10:25-11:05', label: '第3节 10:25-11:05' },
  { value: '11:10-11:50', label: '第4节 11:10-11:50' },
  { value: '14:30-15:10', label: '第5节 14:30-15:10' },
  { value: '15:15-15:55', label: '第6节 15:15-15:55' },
  { value: '16:05-16:45', label: '第7节 16:05-16:45' },
  { value: '16:50-17:30', label: '第8节 16:50-17:30' },
  { value: '19:00-19:40', label: '第9节 19:00-19:40' },
  { value: '19:45-20:25', label: '第10节 19:45-20:25' }
]

const helperForm = reactive({
  labName: '',
  date: '',
  time: '',
  reason: '',
  description: '',
  location: '',
  equipmentHint: '',
  selectedPlanId: ''
})

const adminShortcutActions = [
  { key: 'dailyBrief', label: '今日简报' },
  { key: 'pendingReservations', label: '待审批预约' },
  { key: 'riskAlerts', label: '风险提醒' },
  { key: 'equipmentHealth', label: '设备预测' },
  { key: 'refreshPrediction', label: '刷新预测' }
]

const quickPrompts = [
  '请总结今天最优先的事项',
  '当前待审批预约有多少？',
  '有哪些设备故障风险较高？',
  '列出需要优先关注的设备健康预测'
]

const confirmImportAction = async (item) => {
  if (item.isImporting) return
  item.isImporting = true
  try {
    const resp = await executeAgentImport({ task_id: item.meta.task_id })
    const importedCount = resp?.data?.data?.imported_count || 0
    ElMessage.success(`导入成功！共导入 ${importedCount} 条资产。`)
    item.action = 'import_done'
    appendMessage('assistant', `✅ 录入成功！已将 **${importedCount}** 条资产录入系统。请前往系统后台验证。`)
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || '导入失败')
  } finally {
    item.isImporting = false
  }
}

const cancelImportAction = (item) => {
  item.action = 'import_cancelled'
  appendMessage('user', '取消导入')
  appendMessage('assistant', '已取消资产导入。如有需要请重新上传或发起指令。')
}

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function sourceHost(url) {
  const raw = String(url || '').trim()
  if (!raw) return 'Source'
  try {
    return new URL(raw, window.location.origin).hostname || 'Source'
  } catch (error) {
    return raw.replace(/^https?:\/\//i, '').split('/')[0] || 'Source'
  }
}

function normalizeSources(rawSources) {
  if (!Array.isArray(rawSources)) return []
  return rawSources
    .map((item) => {
      const row = item && typeof item === 'object' ? item : {}
      const title = String(row.title || '').trim()
      const url = String(row.url || '').trim()
      const publishedDate = String(row.publishedDate || row.published_date || '').trim()
      if (!title && !url) return null
      return { title, url, publishedDate }
    })
    .filter(Boolean)
}

function normalizeHelperSlotKey(rawKey = '') {
  const compact = String(rawKey || '')
    .trim()
    .replace(/[\s_-]+/g, '')
    .toLowerCase()
  if (!compact) return ''
  if (['lab', 'labname', 'labid', 'room', 'classroom'].includes(compact)) return 'labName'
  if (['date', 'day'].includes(compact)) return 'date'
  if (['time', 'slot', 'timeslot', 'period'].includes(compact)) return 'time'
  if (['reason', 'purpose'].includes(compact)) return 'reason'
  if (['description', 'desc', 'issue', 'fault'].includes(compact)) return 'description'
  if (['location', 'place'].includes(compact)) return 'location'
  if (['equipmenthint', 'equipmentcode', 'assetcode', 'devicecode', 'equipment'].includes(compact)) return 'equipmentHint'
  if (['selectedplanid', 'plan', 'planid'].includes(compact)) return 'selectedPlanId'
  return String(rawKey || '').trim()
}

function inferHelperMissingSlotsFromText(text = '') {
  const raw = String(text || '').trim()
  if (!raw) return []
  const slots = []
  if (/(实验室|机房|教室|lab)/i.test(raw)) slots.push('labName')
  if (/(日期|哪天|时间日期|yyyy-mm-dd)/i.test(raw)) slots.push('date')
  if (/(时间段|时段|几节|08:00|time)/i.test(raw)) slots.push('time')
  if (/(用途|原因|预约用途)/i.test(raw)) slots.push('reason')
  if (/(故障描述|故障现象|描述)/i.test(raw)) slots.push('description')
  if (/(位置|地点|报修位置)/i.test(raw)) slots.push('location')
  if (/(设备编号|资产编号|编号)/i.test(raw)) slots.push('equipmentHint')
  if (/(方案|plan)/i.test(raw)) slots.push('selectedPlanId')
  return [...new Set(slots)]
}

function normalizeHelperQuestions(rawQuestions) {
  if (!Array.isArray(rawQuestions)) return []
  return rawQuestions
    .map((item) => {
      const row = item && typeof item === 'object' ? item : {}
      const key = normalizeHelperSlotKey(row.key)
      const question = String(row.question || '').trim()
      if (!key && !question) return null
      return { key, question }
    })
    .filter(Boolean)
}

function normalizeHelperPlans(rawPlans) {
  if (!Array.isArray(rawPlans)) return []
  return rawPlans
    .map((item) => {
      const row = item && typeof item === 'object' ? item : {}
      const planId = String(row.planId || '').trim()
      if (!planId) return null
      return {
        planId,
        labName: String(row.labName || '').trim(),
        date: String(row.date || '').trim(),
        time: String(row.time || '').trim(),
        reason: String(row.reason || '').trim()
      }
    })
    .filter(Boolean)
}

function normalizeHelperPending(rawPending) {
  const row = rawPending && typeof rawPending === 'object' ? rawPending : {}
  const slots = row.slots && typeof row.slots === 'object' ? row.slots : {}
  const missingRaw = Array.isArray(row.missingSlots) ? row.missingSlots : Array.isArray(row.missing_slots) ? row.missing_slots : []
  const missingSlots = missingRaw
    .map((item) => normalizeHelperSlotKey(item))
    .filter(Boolean)
  return {
    intent: String(row.intent || '').trim(),
    state: String(row.state || '').trim(),
    slots,
    missingSlots
  }
}

function normalizeAssistantHelper(meta = {}, action = '', replyText = '') {
  if (String(action || '').trim() !== 'ask_info') return null
  const pending = normalizeHelperPending(meta.pending)
  const questions = normalizeHelperQuestions(meta.questions)
  const plans = normalizeHelperPlans(meta.plans)
  let missingSlots = [...pending.missingSlots]
  if (missingSlots.length === 0 && questions.length > 0) {
    missingSlots = questions.map((item) => normalizeHelperSlotKey(item.key)).filter(Boolean)
  }
  if (missingSlots.length === 0) {
    const questionText = questions.map((item) => item.question).join(' ')
    missingSlots = inferHelperMissingSlotsFromText(`${replyText} ${questionText}`)
  }
  missingSlots = [...new Set(missingSlots.filter(Boolean))]
  if (String(action || '').trim() === 'ask_info' && missingSlots.length === 0 && plans.length === 0 && questions.length === 0) {
    return null
  }
  return {
    intent: pending.intent,
    state: pending.state,
    slots: pending.slots,
    missingSlots,
    questions,
    plans
  }
}

function normalizeAgentMessage(item = {}) {
  const meta = item.meta && typeof item.meta === 'object' ? item.meta : {}
  const action = String(item.action || '').trim()
  return {
    id: item.id || createMessageId(),
    role: item.role === 'user' ? 'user' : 'assistant',
    text: String(item.text || '').trim(),
    createdAt: item.createdAt || new Date().toLocaleTimeString(),
    action,
    meta,
    sources: normalizeSources(meta.sources),
    helper: item.role === 'assistant' ? normalizeAssistantHelper(meta, action, item.text) : null,
    files: Array.isArray(meta.files) ? meta.files : []
  }
}

function appendMessage(role, text, sources = [], extra = {}) {
  const helper = role === 'assistant' ? normalizeAssistantHelper(extra, extra.action, text) : null
  messages.value.push({
    id: createMessageId(),
    role,
    text: String(text || '').trim(),
    createdAt: new Date().toLocaleTimeString(),
    action: String(extra.action || '').trim(),
    meta: extra,
    sources: normalizeSources(sources),
    helper,
    files: Array.isArray(extra.files) ? extra.files : []
  })
}

function helperSlotLabel(slot) {
  const key = String(slot || '').trim()
  if (key === 'labName') return '实验室'
  if (key === 'date') return '日期'
  if (key === 'time') return '时间段'
  if (key === 'reason') return '用途'
  if (key === 'description') return '故障描述'
  if (key === 'location') return '报修位置'
  if (key === 'equipmentHint') return '设备编号'
  if (key === 'selectedPlanId') return '方案'
  return key || '补充信息'
}

function buildHelperDateOptions() {
  const formatter = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'short' })
  const items = []
  for (let i = 0; i < 7; i += 1) {
    const date = new Date()
    date.setDate(date.getDate() + i)
    const value = date.toLocaleDateString('sv-SE')
    const prefix = i === 0 ? '今天' : i === 1 ? '明天' : i === 2 ? '后天' : ''
    const label = prefix ? `${prefix} ${formatter.format(date)}` : formatter.format(date)
    items.push({ value, label })
  }
  return items
}

function resetHelperForm() {
  helperForm.labName = ''
  helperForm.date = ''
  helperForm.time = ''
  helperForm.reason = ''
  helperForm.description = ''
  helperForm.location = ''
  helperForm.equipmentHint = ''
  helperForm.selectedPlanId = ''
}

async function loadHelperLabs() {
  if (helperLabsLoading.value || helperLabOptions.value.length > 0) return
  helperLabsLoading.value = true
  try {
    const response = await getLabs()
    const rows = Array.isArray(response?.data?.data) ? response.data.data : []
    helperLabOptions.value = rows
      .map((item) => ({
        id: Number(item.id || 0),
        name: String(item.name || '').trim()
      }))
      .filter((item) => item.name)
  } finally {
    helperLabsLoading.value = false
  }
}

function fillHelperForm(helper) {
  resetHelperForm()
  const slots = helper?.slots && typeof helper.slots === 'object' ? helper.slots : {}
  helperForm.labName = String(slots.labName || '').trim()
  helperForm.date = String(slots.date || '').trim()
  helperForm.time = String(slots.time || '').trim()
  helperForm.reason = String(slots.reason || '').trim()
  helperForm.description = String(slots.description || '').trim()
  helperForm.location = String(slots.location || '').trim()
  helperForm.equipmentHint = String(slots.equipmentHint || '').trim()
  helperForm.selectedPlanId = String(slots.selectedPlanId || '').trim()
}

async function openHelperPanel(helper) {
  if (!helper) return
  if (!Array.isArray(helper.missingSlots) || (helper.missingSlots.length === 0 && (!Array.isArray(helper.plans) || helper.plans.length === 0) && (!Array.isArray(helper.questions) || helper.questions.length === 0))) {
    return
  }
  activeHelper.value = helper
  fillHelperForm(helper)
  helperDateOptions.value = buildHelperDateOptions()
  helperPanelVisible.value = true
  if (helper.missingSlots.includes('labName')) {
    await loadHelperLabs()
  }
}

function shouldShowHelperField(field) {
  const helper = activeHelper.value
  if (!helper) return false
  if (field === 'selectedPlanId') return Array.isArray(helper.plans) && helper.plans.length > 0
  return helper.missingSlots.includes(field)
}

function handleHelperLabSelectOpen(opened) {
  if (opened) loadHelperLabs()
}

function selectHelperPlan(plan) {
  const row = plan && typeof plan === 'object' ? plan : {}
  helperForm.selectedPlanId = String(row.planId || '').trim()
  if (row.labName) helperForm.labName = row.labName
  if (row.date) helperForm.date = row.date
  if (row.time) helperForm.time = row.time
}

function buildHelperSubmitText() {
  const intent = String(activeHelper.value?.intent || '').trim()
  const missingSlots = Array.isArray(activeHelper.value?.missingSlots) ? activeHelper.value.missingSlots : []
  const lines = []
  if (intent === 'reserve_query' || (!intent && missingSlots.includes('labName') && (missingSlots.includes('date') || hasHelperValue(helperForm.date)) && (missingSlots.includes('time') || hasHelperValue(helperForm.time)))) {
    return `帮我查询 ${helperForm.labName || '该实验室'} ${helperForm.date || ''} ${helperForm.time || ''} 是否已被预约`.replace(/\s+/g, ' ').trim()
  }
  if (intent === 'reserve_create') {
    const reasonText = helperForm.reason ? `，用途：${helperForm.reason}` : ''
    return `帮我预约 ${helperForm.labName || '该实验室'} ${helperForm.date || ''} ${helperForm.time || ''}${reasonText}`.replace(/\s+/g, ' ').trim()
  }
  if (intent === 'repair_create') {
    const target = helperForm.equipmentHint || helperForm.location || helperForm.labName || '该位置'
    return `帮我提交报修，位置：${target}；故障描述：${helperForm.description || '待补充'}`
  }
  if (helperForm.selectedPlanId) lines.push(`我选择方案 ${helperForm.selectedPlanId}`)
  if (helperForm.labName) lines.push(`实验室名称：${helperForm.labName}`)
  if (helperForm.date) lines.push(`日期：${helperForm.date}`)
  if (helperForm.time) lines.push(`时间段：${helperForm.time}`)
  if (helperForm.reason) lines.push(`用途：${helperForm.reason}`)
  if (helperForm.description) lines.push(`故障描述：${helperForm.description}`)
  if (helperForm.location) lines.push(`报修位置：${helperForm.location}`)
  if (helperForm.equipmentHint) lines.push(`设备编号：${helperForm.equipmentHint}`)
  return lines.join('；')
}

function hasHelperValue(value) {
  return Boolean(String(value || '').trim())
}

const helperPanelTitle = computed(() => {
  const intent = String(activeHelper.value?.intent || '').trim()
  if (intent === 'reserve_create') return '补充预约信息'
  if (intent === 'reserve_query') return '补充查询条件'
  if (intent === 'repair_create') return '补充报修信息'
  return '补充信息'
})

const activeHelperQuestions = computed(() => activeHelper.value?.questions || [])
const activeHelperPlans = computed(() => activeHelper.value?.plans || [])
const showHelperPlans = computed(() => activeHelperPlans.value.length > 0)
const canSubmitHelperForm = computed(() => {
  return [
    helperForm.selectedPlanId,
    helperForm.labName,
    helperForm.date,
    helperForm.time,
    helperForm.reason,
    helperForm.description,
    helperForm.location,
    helperForm.equipmentHint
  ].some(hasHelperValue)
})

async function submitHelperPanel() {
  const text = buildHelperSubmitText()
  if (!text) {
    ElMessage.warning('请先选择或填写至少一项补充信息')
    return
  }
  helperPanelVisible.value = false
  await sendChatText(text)
}

function buildStatsSource(title = '管理后台统计快照', url = '/admin/stats/dashboard', publishedDate = '') {
  return [{ title, url, publishedDate }]
}

function formatDailyBriefMessage(brief = {}) {
  const summary = String(brief.summaryText || '').trim() || '暂无今日 AI 简报。'
  const highlights = Array.isArray(brief.highlights) ? brief.highlights.filter(Boolean) : []
  const actions = Array.isArray(brief.focusActions) ? brief.focusActions.filter((item) => item && item.title) : []
  const lines = [summary]
  if (highlights.length) {
    lines.push('', '重点事项：')
    highlights.slice(0, 5).forEach((item, index) => {
      lines.push(`${index + 1}. ${item}`)
    })
  }
  if (actions.length) {
    lines.push('', '建议动作：')
    actions.slice(0, 4).forEach((item, index) => {
      lines.push(`${index + 1}. ${item.title}`)
    })
  }
  return lines.join('\n')
}

function formatRiskAlertsMessage(alerts = []) {
  const rows = Array.isArray(alerts) ? alerts.filter(Boolean) : []
  if (!rows.length) return '当前暂无风险提醒。'
  const lines = ['当前风险提醒如下：']
  rows.slice(0, 6).forEach((item, index) => {
    const level = String(item.level || '').trim() || 'low'
    const score = Number(item.score || 0)
    const description = String(item.description || '').trim()
    lines.push(`${index + 1}. ${item.title || '未命名提醒'} [${level}]${score ? ` 风险分 ${Math.round(score)}` : ''}${description ? `：${description}` : ''}`)
  })
  return lines.join('\n')
}

function formatEquipmentHealthMessage(items = []) {
  const rows = Array.isArray(items) ? items.filter(Boolean) : []
  if (!rows.length) return '当前暂无设备健康预测数据。'
  const lines = ['当前设备健康预测重点如下：']
  rows.slice(0, 6).forEach((item, index) => {
    const riskScore = Number(item.riskScore || 0)
    const riskLevel = String(item.riskLevel || '').trim() || 'low'
    const name = String(item.name || item.assetCode || `设备 ${index + 1}`).trim()
    const code = String(item.assetCode || '').trim()
    const recommendation = String(item.recommendation || '').trim()
    lines.push(`${index + 1}. ${name}${code ? `（${code}）` : ''}，风险等级 ${riskLevel}，风险分 ${Math.round(riskScore)}${recommendation ? `。建议：${recommendation}` : ''}`)
  })
  return lines.join('\n')
}

function buildErrorText(error, timeoutText = 'AI 响应时间较长，请稍后重试。') {
  const isTimeout = String(error?.code || '').toUpperCase() === 'ECONNABORTED' || String(error?.message || '').toLowerCase().includes('timeout')
  if (isTimeout) return timeoutText
  return String(error?.response?.data?.msg || error?.message || '').trim() || '当前暂时无法连接 AI 助手，请稍后重试。'
}

async function withChatLoading(task) {
  if (chatLoading.value) return
  chatLoading.value = true
  try {
    await task()
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

async function loadHistory(showToast = true) {
  pageLoading.value = true
  try {
    const response = await getAgentHistory({ limit: 80 })
    const rows = response?.data?.data?.messages || []
    messages.value = Array.isArray(rows) ? rows.map(normalizeAgentMessage) : []
    const lastHelperMessage = [...messages.value].reverse().find((item) => item?.role === 'assistant' && item?.helper)
    if (lastHelperMessage?.helper) {
      await openHelperPanel(lastHelperMessage.helper)
    }
    await scrollToBottom()
    if (showToast) {
      ElMessage.success(`已加载 ${messages.value.length} 条会话记录`)
    }
  } finally {
    pageLoading.value = false
  }
}

async function reloadAll() {
  await loadHistory(false)
  ElMessage.success('已刷新会话内容')
}

async function handleClearHistory() {
  await clearAgentHistory()
  messages.value = []
  ElMessage.success('已清空当前会话历史')
}

async function fetchDailyBriefToChat() {
  appendMessage('user', '查看今日 AI 简报')
  await withChatLoading(async () => {
    const response = await getAdminAiDailyBrief()
    const brief = response?.data?.data || {}
    appendMessage('assistant', formatDailyBriefMessage(brief), buildStatsSource('AI 每日简报', '/admin/ai/daily-brief', String(brief.generatedAt || '')))
  })
}

async function askAdminStatsQuestion(question) {
  const text = String(question || '').trim()
  if (!text) return
  appendMessage('user', text)
  await withChatLoading(async () => {
    const response = await queryAdminStatsAi({ question: text })
    const payload = response?.data?.data || {}
    appendMessage('assistant', String(payload.answer || '暂无统计结果。').trim(), buildStatsSource())
  })
}

async function fetchRiskAlertsToChat() {
  appendMessage('user', '查看风险提醒')
  await withChatLoading(async () => {
    const response = await getAdminAiRiskAlerts()
    const alerts = response?.data?.data?.alerts || []
    const sources = (Array.isArray(alerts) ? alerts : []).slice(0, 6).map((item) => ({
      title: String(item?.title || '风险提醒').trim(),
      url: String(item?.jumpUrl || '/notification-center').trim()
    }))
    appendMessage('assistant', formatRiskAlertsMessage(alerts), sources.length ? sources : buildStatsSource('风险提醒', '/admin/ai/risk-alerts'))
  })
}

async function fetchEquipmentHealthToChat(refreshFirst = false) {
  appendMessage('user', refreshFirst ? '刷新设备健康预测' : '查看设备健康预测')
  await withChatLoading(async () => {
    if (refreshFirst) {
      await refreshAdminAiEquipmentHealth({ horizonDaysList: [7, 30] })
    }
    const response = await getAdminAiEquipmentHealth({ limit: 6 })
    const items = response?.data?.data?.items || []
    const sources = (Array.isArray(items) ? items : []).slice(0, 6).map((item) => ({
      title: String(item?.name || item?.assetCode || '设备预测').trim(),
      url: String(item?.jumpUrl || '/equipments').trim()
    }))
    appendMessage(
      'assistant',
      `${refreshFirst ? '已刷新设备健康预测。\n' : ''}${formatEquipmentHealthMessage(items)}`,
      sources.length ? sources : buildStatsSource('设备健康预测', '/admin/ai/equipment-health')
    )
  })
}

async function runShortcutAction(key) {
  try {
    if (key === 'dailyBrief') {
      await fetchDailyBriefToChat()
      return
    }
    if (key === 'pendingReservations') {
      await askAdminStatsQuestion('当前待审批预约有多少？')
      return
    }
    if (key === 'riskAlerts') {
      await fetchRiskAlertsToChat()
      return
    }
    if (key === 'equipmentHealth') {
      await fetchEquipmentHealthToChat(false)
      return
    }
    if (key === 'refreshPrediction') {
      await fetchEquipmentHealthToChat(true)
    }
  } catch (error) {
    appendMessage('assistant', buildErrorText(error, '当前快捷能力暂时不可用，请稍后重试。'))
  }
}

async function handleHeaderCommand(command) {
  await runShortcutAction(String(command || '').trim())
}

function triggerFileUpload() {
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  await handleSingleFileUpload(file)
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function loadFiles() {
  fileManagerLoading.value = true
  try {
    const response = await getAgentFiles()
    uploadedFiles.value = Array.isArray(response?.data?.data?.files) ? response.data.data.files : []
    // Clean up selectedFileIds if files were deleted elsewhere
    const availableIds = uploadedFiles.value.map(f => f.id)
    selectedFileIds.value = selectedFileIds.value.filter(id => availableIds.includes(id))
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  } finally {
    fileManagerLoading.value = false
  }
}

function toggleFileSelection(id, val) {
  if (val && !selectedFileIds.value.includes(id)) {
    selectedFileIds.value.push(id)
  } else if (!val) {
    selectedFileIds.value = selectedFileIds.value.filter(x => x !== id)
  }
}

async function handleToggleKnowledge(file) {
  try {
    const targetStatus = file.inKnowledge === 1 || file.in_knowledge === 1 ? 1 : 0
    await toggleAgentFileKnowledge(file.id, { inKnowledge: targetStatus })
    ElMessage.success(targetStatus === 1 ? '已加入全局知识库' : '已移出全局知识库')
  } catch (error) {
    if ('inKnowledge' in file) {
      file.inKnowledge = file.inKnowledge === 1 ? 0 : 1
    } else if ('in_knowledge' in file) {
      file.in_knowledge = file.in_knowledge === 1 ? 0 : 1
    }
    ElMessage.error('更改知识库状态失败')
  }
}

async function handleDeleteFile(id) {
  try {
    await deleteAgentFile(id)
    ElMessage.success('已删除文件')
    selectedFileIds.value = selectedFileIds.value.filter(x => x !== id)
    await loadFiles()
  } catch (error) {
    ElMessage.error('删除文件失败')
  }
}

function submitWebSearch() {
  chatInput.value = '请联网搜索实验室管理相关的最新政策或设备资料，并给我简要总结'
  submitChat()
}

async function sendChatText(text, options = {}) {
  const {
    appendUser = true,
    displayText = text
  } = options
  const content = String(text || '').trim()
  if (!content) return

  const payloadFileIds = [...selectedFileIds.value]
  const attachedFiles = uploadedFiles.value.filter(f => payloadFileIds.includes(f.id))
  
  if (appendUser) {
    appendMessage('user', displayText, [], { files: attachedFiles })
  }

  selectedFileIds.value = []
  chatInput.value = ''
  await withChatLoading(async () => {
    const response = await chatWithAgent({ text: content, fileIds: payloadFileIds })
    const payload = response?.data?.data || {}
    const reply = String(payload.reply || '').trim() || '助手暂时没有返回内容。'
    const helper = normalizeAssistantHelper(payload, payload.action)
    appendMessage('assistant', reply, payload.sources, payload)
    if (helper) {
      await nextTick()
      await openHelperPanel(helper)
    }
  })
}

async function submitChat() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return

  try {
    await sendChatText(text)
  } catch (error) {
    console.error('agent chat failed:', error)
    appendMessage('assistant', buildErrorText(error, 'AI 响应时间较长，前端请求已超时。请稍后重试，或继续让我帮你调大聊天接口超时时间。'))
    await scrollToBottom()
  }
}

async function usePrompt(prompt) {
  await sendChatText(prompt)
}

function findNearestUserText(index) {
  for (let i = Number(index); i >= 0; i -= 1) {
    const row = messages.value[i]
    if (row && row.role === 'user' && row.text) {
      return String(row.text).trim()
    }
  }
  return ''
}

async function regenerateMessage(index) {
  const sourceText = findNearestUserText(index)
  if (!sourceText) {
    ElMessage.warning('未找到可重新生成的用户问题')
    return
  }
  try {
    await sendChatText(sourceText, { appendUser: false })
  } catch (error) {
    appendMessage('assistant', buildErrorText(error, '重新生成失败，请稍后重试。'))
  }
}

async function copyMessage(text) {
  const content = String(text || '').trim()
  if (!content) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(content)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = content
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    ElMessage.success('已复制消息内容')
  } catch (error) {
    ElMessage.error('复制失败，请检查浏览器权限')
  }
}

function initSpeechRecognition() {
  if (typeof window === 'undefined') return
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  speechSupported.value = Boolean(SpeechRecognition)
  if (!SpeechRecognition) return

  speechRecognizer = new SpeechRecognition()
  speechRecognizer.lang = 'zh-CN'
  speechRecognizer.interimResults = true
  speechRecognizer.continuous = false

  speechRecognizer.onresult = (event) => {
    const transcript = Array.from(event.results || [])
      .map((item) => item?.[0]?.transcript || '')
      .join('')
      .trim()
    recognizedSpeech.value = transcript
    if (transcript) {
      chatInput.value = transcript
    }
  }

  speechRecognizer.onerror = () => {
    isRecording.value = false
    shouldSendVoiceResult = false
    ElMessage.error('语音识别失败，请稍后重试')
  }

  speechRecognizer.onend = async () => {
    const text = String(recognizedSpeech.value || '').trim()
    const shouldSend = shouldSendVoiceResult
    isRecording.value = false
    shouldSendVoiceResult = false
    recognizedSpeech.value = ''
    if (shouldSend && text) {
      try {
        await sendChatText(text)
      } catch (error) {
        appendMessage('assistant', buildErrorText(error, '语音消息发送失败，请稍后重试。'))
      }
    }
  }
}

function toggleVoiceInput() {
  if (!speechSupported.value || !speechRecognizer) {
    ElMessage.warning('当前浏览器不支持语音输入')
    return
  }
  if (isRecording.value) {
    speechRecognizer.stop()
    return
  }
  try {
    recognizedSpeech.value = ''
    shouldSendVoiceResult = true
    isRecording.value = true
    speechRecognizer.start()
  } catch (error) {
    isRecording.value = false
    shouldSendVoiceResult = false
    ElMessage.error('无法启动语音识别')
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTo({ top: chatBodyRef.value.scrollHeight, behavior: 'smooth' })
  }
}

onMounted(() => {
  helperDateOptions.value = buildHelperDateOptions()
  initSpeechRecognition()
  loadHistory(false)
  loadFiles()
})

onBeforeUnmount(() => {
  if (speechRecognizer && isRecording.value) {
    try {
      speechRecognizer.stop()
    } catch (error) {}
  }
})
</script>

<style scoped lang="scss">
$primary-blue: #3b82f6;
$bg-light: #f8fafc;
$text-dark: #1e293b;
$text-secondary: #64748b;
$card-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
$radius-xl: 20px;
$radius-lg: 16px;

.page-container {
  min-height: 100vh;
  background-color: $bg-light;
  background-image:
    radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.03) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(147, 51, 234, 0.03) 0px, transparent 50%);
  padding: 24px;
  box-sizing: border-box;
}

.workspace-shell {
  height: 100%;
}

.workspace-main {
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 48px);
}

.chat-panel {
  height: 100%;
  background: #ffffff;
  border-radius: $radius-xl;
  box-shadow: $card-shadow;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(226, 232, 240, 0.5);
}

.chat-header {
  height: 64px;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  z-index: 10;

  .assistant-title-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .ai-avatar-mini {
      width: 32px;
      height: 32px;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    h2 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: $text-dark;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .version-tag {
      font-size: 11px;
      background: #f1f5f9;
      color: $text-secondary;
      padding: 2px 8px;
      border-radius: 20px;
      font-weight: 400;
    }
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;

  .divider-v {
    width: 1px;
    height: 16px;
    background: #e2e8f0;
  }
}

.assistant-shortcuts {
  display: flex;
  gap: 10px;
  padding: 12px 24px;
  overflow-x: auto;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.8), rgba(255, 255, 255, 0.95));

  &::-webkit-scrollbar {
    display: none;
  }
}

.shortcut-chip {
  flex-shrink: 0;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: $primary-blue;
  font-size: 13px;

  &:hover {
    background: #dbeafe;
    border-color: #93c5fd;
  }
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 40px 10%;
  scroll-behavior: smooth;

  &::-webkit-scrollbar {
    width: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 10px;
  }
}

.welcome-container {
  margin-top: 5vh;
}

.welcome-card {
  margin-bottom: 40px;

  .gemini-greeting {
    font-size: 48px;
    margin-bottom: 16px;
    font-weight: 700;

    .gradient-text {
      background: linear-gradient(90deg, #4285f4, #9b72cb, #d96570);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
  }

  .gemini-subtitle {
    font-size: 18px;
    color: $text-secondary;
    line-height: 1.6;

    .text-highlight {
      color: $primary-blue;
      font-weight: 500;
    }
  }
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;

  .quick-card-item {
    background: #f8fafc;
    border: 1px solid #f1f5f9;
    border-radius: $radius-lg;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    gap: 12px;
    position: relative;

    .card-icon {
      font-size: 20px;
      color: $primary-blue;
    }

    .card-text {
      font-size: 14px;
      color: $text-dark;
      line-height: 1.4;
    }

    .card-arrow {
      position: absolute;
      right: 16px;
      bottom: 16px;
      font-size: 14px;
      color: $text-secondary;
      opacity: 0;
      transform: translate(-4px, 4px);
    }

    &:hover {
      background: #ffffff;
      border-color: $primary-blue;
      transform: translateY(-4px);
      box-shadow: 0 10px 20px rgba(59, 130, 246, 0.05);

      .card-arrow {
        opacity: 1;
        transform: translate(0, 0);
      }
    }
  }
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.message-row {
  display: flex;
  gap: 16px;
  animation: fadeInUp 0.4s ease-out;
}

.message-row--user {
  justify-content: flex-end;
}

.message-avatar-wrap {
  flex-shrink: 0;

  .ai-avatar-inner {
    width: 36px;
    height: 36px;
    background: #fff;
    border-radius: 10px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }
}

.message-content {
  max-width: 80%;
  display: flex;
  flex-direction: column;
  gap: 6px;

  .message-meta {
    font-size: 11px;
    color: #94a3b8;
  }
}

.message-content--user {
  align-items: flex-end;
}

.message-bubble {
  padding: 12px 18px;
  font-size: 15px;
  line-height: 1.6;
}

.message-bubble--user {
  background: $primary-blue;
  color: #fff;
  border-radius: 18px 4px 18px 18px;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15);
}

.message-bubble--assistant {
  color: $text-dark;
  border-radius: 4px 18px 18px 18px;
  padding: 0;
}

.message-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-tools {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}

.source-container {
  margin-top: 16px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #f1f5f9;

  .source-tag-header {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .source-flex {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .source-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    text-decoration: none;
    color: $text-dark;
    font-size: 12px;
    transition: all 0.2s;

    &:hover {
      border-color: $primary-blue;
      transform: translateY(-1px);
    }

    .sc-idx {
      width: 14px;
      height: 14px;
      background: #f1f5f9;
      color: $text-secondary;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
    }
  }
}

.composer-wrapper {
  padding: 0 10% 32px;
  background: linear-gradient(to top, #fff 80%, rgba(255, 255, 255, 0));
}

.composer-inner {
  background: #f0f4f9;
  border-radius: 24px;
  padding: 8px 16px;
  border: 2px solid transparent;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);

  &.is-focused {
    background: #fff;
    border-color: rgba(59, 130, 246, 0.3);
    box-shadow: 0 10px 30px rgba(59, 130, 246, 0.08);
  }

  .composer-textarea {
    :deep(.el-textarea__inner) {
      background: transparent;
      border: none;
      box-shadow: none;
      padding: 12px 0;
      font-size: 15px;
      color: $text-dark;

      &::placeholder {
        color: #94a3b8;
      }
    }
  }
}

.composer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;

  .tool-btn {
    border: none;
    background: transparent;
    color: $text-secondary;

    &.is-active {
      background: #dbeafe;
      color: $primary-blue;
    }

    &:hover {
      background: #e2e8f0;
      color: $text-dark;
    }
  }

  .send-pill {
    border-radius: 20px;
    padding: 0 20px;
    font-weight: 500;
  }
}

.composer-hint {
  text-align: center;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 12px;

  .kbd {
    background: #f1f5f9;
    padding: 2px 4px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
  }
}

:deep(.pending-helper-drawer .el-drawer__body) {
  padding: 0;
}

.pending-helper-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  overflow-y: auto;
}

.pending-helper-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h3 {
    margin: 0;
    font-size: 22px;
    color: $text-dark;
  }

  p {
    margin: 8px 0 0;
    color: $text-secondary;
    line-height: 1.6;
  }
}

.pending-helper-section,
.pending-helper-summary {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.pending-helper-label {
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.pending-helper-tags,
.pending-helper-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.helper-chip {
  border: 1px solid rgba(96, 165, 250, 0.35);
  background: #fff;
  color: #1e3a8a;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.helper-chip.is-active,
.helper-chip:hover {
  background: #dbeafe;
  border-color: #60a5fa;
}

.pending-helper-tips {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pending-helper-tip {
  font-size: 14px;
  line-height: 1.7;
  color: $text-dark;
}

.plan-option-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.plan-option-card {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: #fff;
  border-radius: 18px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;

  p {
    margin: 8px 0 0;
    color: $text-secondary;
    line-height: 1.6;
  }
}

.plan-option-card.is-active,
.plan-option-card:hover {
  border-color: #60a5fa;
  background: #eff6ff;
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
}

.plan-option-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: $text-dark;
}

.pending-helper-date-picker {
  width: 100%;
  margin-top: 14px;
}

.pending-helper-footer {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

@media (max-width: 1024px) {
  .page-container {
    padding: 16px;
  }

  .workspace-main {
    height: calc(100vh - 32px);
  }

  .chat-body,
  .composer-wrapper {
    padding-left: 24px;
    padding-right: 24px;
  }

  .welcome-card .gemini-greeting {
    font-size: 36px;
  }
}

@media (max-width: 768px) {
  .chat-header {
    padding: 0 16px;
  }

  .assistant-shortcuts {
    padding: 10px 16px;
  }

  .chat-body {
    padding: 24px 16px;
  }

  .composer-wrapper {
    padding: 0 16px 20px;
  }

  .quick-grid {
    grid-template-columns: 1fr;
  }

  .message-content {
    max-width: 92%;
  }

  .header-actions {
    gap: 8px;
  }

  .pending-helper-panel {
    padding: 20px 16px;
  }
}

/* 动画 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-in-up { animation: fadeInUp 0.6s ease-out forwards; }
.fade-in-up-delay { animation: fadeInUp 0.6s ease-out 0.2s forwards; opacity: 0; }

.file-manager-drawer {
  .file-manager-container {
    padding: 20px;
    display: flex;
    flex-direction: column;
    height: 100%;
    
    .file-manager-desc {
      font-size: 13px;
      color: #64748b;
      margin-bottom: 16px;
      line-height: 1.5;
      background: #f8fafc;
      padding: 10px;
      border-radius: 8px;
    }
    
    .file-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      
      .file-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        transition: all 0.2s;
        
        &:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.05);
        }

        .file-item-left {
          display: flex;
          align-items: center;
          gap: 10px;
          overflow: hidden;

          .file-icon {
            font-size: 20px;
            color: #3b82f6;
          }

          .file-info {
            display: flex;
            flex-direction: column;
            overflow: hidden;

            .file-name {
              font-size: 14px;
              color: #1e293b;
              font-weight: 500;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .file-meta {
              font-size: 12px;
              color: #94a3b8;
              margin-top: 2px;
            }
          }
        }
        
        .file-item-right {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-shrink: 0;
        }
      }
    }
  }
}
.selected-files-area {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 16px 0;
  margin-bottom: 8px;
}
.selected-file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #1e3a8a;
  
  .file-name {
    max-width: 150px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .remove-icon {
    cursor: pointer;
    font-size: 14px;
    color: #94a3b8;
    &:hover {
      color: #ef4444;
    }
  }
}
.composer-inner.is-dragging {
  border-color: #3b82f6;
  background: #f0fdf4;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}
.message-attached-files-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.3);
  padding-top: 8px;
}
.message-row--user .message-attached-files-list {
  border-top-color: rgba(255, 255, 255, 0.3);
}
.message-row--assistant .message-attached-files-list {
  border-top-color: rgba(0, 0, 0, 0.08);
}
.attached-file-chip-bubble {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 10px;
  border-radius: 6px;
  width: fit-content;
}
.message-row--assistant .attached-file-chip-bubble {
  background: #f1f5f9;
  color: #475569;
}
</style>



