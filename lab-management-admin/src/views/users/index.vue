<template>
  <div class="page-wrap">
    <section class="page-head">
      <div>
        <span class="eyebrow">账号治理</span>
        <h2>用户管理</h2>
        <p>支持单个创建、批量生成学生账号、文本导入、毕业生批量停用，以及现有账号治理能力。</p>
      </div>
      <div class="head-actions">
        <el-button @click="openGraduateDialog">毕业生停用</el-button>
        <el-button @click="openImportDialog">文本导入</el-button>
        <el-button @click="openBatchDialog">批量生成学生</el-button>
        <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
      </div>
    </section>

    <section class="page-card">
      <el-form inline class="filter-form">
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="账号 / 昵称 / 班级 / 手机号" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="filters.role" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="教师" value="teacher" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="filters.className" placeholder="如：计科2301" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="毕业年份">
          <el-input-number v-model="filters.graduationYear" :min="2000" :max="2200" :controls="false" placeholder="可选" style="width: 140px" />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-select v-model="filters.activeState" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="正常" value="active" />
            <el-option label="停用" value="inactive" />
            <el-option label="冻结" value="frozen" />
          </el-select>
        </el-form-item>
        <el-form-item label="登录状态">
          <el-select v-model="filters.neverLoggedIn" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="从未登录" value="yes" />
            <el-option label="至少登录过" value="no" />
          </el-select>
        </el-form-item>
        <el-form-item label="违规情况">
          <el-select v-model="filters.hasViolation" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="有违规" value="yes" />
            <el-option label="无违规" value="no" />
          </el-select>
        </el-form-item>
        <el-form-item label="最近登录">
          <el-select v-model="filters.loginDays" style="width: 160px">
            <el-option label="全部" value="all" />
            <el-option label="近 7 天" value="7" />
            <el-option label="近 30 天" value="30" />
            <el-option label="近 90 天" value="90" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="resetFilters">重置筛选</el-button>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询用户</el-button>
        </el-form-item>
      </el-form>

      <div class="quick-filter-row">
        <span class="quick-filter-label">快捷筛选</span>
        <el-button
          v-for="item in quickFilterOptions"
          :key="item.value"
          size="small"
          :type="filters.quickFilter === item.value ? 'primary' : 'default'"
          plain
          @click="applyQuickFilter(item.value)"
        >
          {{ item.label }}
        </el-button>
      </div>

      <div class="governance-grid">
        <button
          v-for="item in governanceCards"
          :key="item.quickFilter"
          type="button"
          class="governance-card"
          :class="{ active: filters.quickFilter === item.quickFilter }"
          @click="applyQuickFilter(item.quickFilter)"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </button>
      </div>

      <div class="governance-toolbar">
        <span class="quick-filter-label">毕业治理年份</span>
        <el-input-number
          v-model="filters.graduateReferenceYear"
          :min="2000"
          :max="2200"
          :controls="false"
          style="width: 140px"
          @change="handleGraduateReferenceYearChange"
        />
      </div>

      <div v-if="activeQuickFilterMeta" class="quick-filter-hint">
        <div>
          <strong>当前筛选：{{ activeQuickFilterMeta.label }}</strong>
          <p>{{ activeQuickFilterMeta.description }}</p>
        </div>
        <el-button link type="primary" @click="applyQuickFilter('all')">查看全部用户</el-button>
      </div>

      <div class="summary-grid">
        <article class="summary-card">
          <span>当前总用户</span>
          <strong>{{ total }}</strong>
        </article>
        <article class="summary-card">
          <span>本页管理员</span>
          <strong>{{ pageRoleSummary.admin }}</strong>
        </article>
        <article class="summary-card">
          <span>本页教师</span>
          <strong>{{ pageRoleSummary.teacher }}</strong>
        </article>
        <article class="summary-card">
          <span>本页学生</span>
          <strong>{{ pageRoleSummary.student }}</strong>
        </article>
      </div>

      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="username" label="账号" min-width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column prop="className" label="班级" min-width="140" />
        <el-table-column prop="graduationYear" label="毕业年份" width="110" />
        <el-table-column label="角色" width="160">
          <template #default="{ row }">
            <el-select v-model="row.role" size="small" style="width: 120px" @change="changeRole(row)">
              <el-option label="管理员" value="admin" />
              <el-option label="教师" value="teacher" />
              <el-option label="学生" value="student" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.isFrozen ? 'danger' : row.isActive ? 'success' : 'info'">
              {{ row.isFrozen ? '冻结' : row.isActive ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="违规记录" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.hasViolation ? 'warning' : 'success'">
              {{ row.violationCount || 0 }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="最近登录" min-width="180" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
            <el-button link @click="toggleFreeze(row)">{{ row.isFrozen ? '解冻' : '冻结' }}</el-button>
            <el-button link @click="handleResetPassword(row)">重置密码</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="当前筛选条件下暂无用户数据" />
        </template>
      </el-table>

      <div class="pager-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="fetchRows"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>

    <el-drawer v-model="detailVisible" title="用户详情" size="720px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="账号">{{ detail.user?.username || '-' }}</el-descriptions-item>
            <el-descriptions-item label="角色">{{ detail.user?.role || '-' }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ detail.user?.nickname || '-' }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ detail.user?.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="班级">{{ detail.user?.className || '-' }}</el-descriptions-item>
            <el-descriptions-item label="毕业年份">{{ detail.user?.graduationYear || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最近登录">{{ detail.user?.lastLoginAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="违规次数">{{ detail.user?.violationCount || 0 }}</el-descriptions-item>
          </el-descriptions>

          <section class="detail-section">
            <div class="detail-section-head">
              <h3>AI 权限</h3>
              <el-button size="small" :loading="aiPermissionLoading" @click="refreshDetailAiPermissions">刷新</el-button>
            </div>
            <el-table :data="detailAiPermissionRows" size="small">
              <el-table-column prop="permissionCode" label="权限码" min-width="220" />
              <el-table-column label="状态" width="140">
                <template #default="{ row }">
                  <el-tag size="small" :type="aiPermissionTagType(row)">{{ aiPermissionStatusLabel(row) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="140">
                <template #default="{ row }">
                  {{ aiPermissionSourceLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column label="过期时间" min-width="180">
                <template #default="{ row }">
                  {{ row.expiresAt || (row.granted ? '长期有效' : '-') }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canGrantAiPermission(detail?.user)"
                    :loading="aiPermissionLoading"
                    @click="handleGrantAiPermission(row.permissionCode)"
                  >
                    授权
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    :disabled="!canRevokeAiPermission(detail?.user, row)"
                    :loading="aiPermissionLoading"
                    @click="handleRevokeAiPermission(row.permissionCode)"
                  >
                    撤销
                  </el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无 AI 权限信息" :image-size="70" />
              </template>
            </el-table>
            <p class="detail-tip">当前页面仅开放 `ai.reservation.view_owner` 的查看、授权与撤销。</p>
          </section>

          <section class="detail-section">
            <h3>汇总数据</h3>
            <div class="detail-summary-grid">
              <article class="summary-card">
                <span>预约数</span>
                <strong>{{ detail.summary?.reservationTotal || 0 }}</strong>
              </article>
              <article class="summary-card">
                <span>报修数</span>
                <strong>{{ detail.summary?.repairTotal || 0 }}</strong>
              </article>
              <article class="summary-card">
                <span>失物招领</span>
                <strong>{{ detail.summary?.lostFoundTotal || 0 }}</strong>
              </article>
              <article class="summary-card">
                <span>违规记录</span>
                <strong>{{ detail.summary?.violationTotal || 0 }}</strong>
              </article>
            </div>
          </section>

          <section class="detail-section">
            <h3>最近预约</h3>
            <el-table :data="detail.reservations || []" size="small">
              <el-table-column prop="labName" label="实验室" min-width="140" />
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="status" label="状态" width="100" />
              <el-table-column prop="createdAt" label="提交时间" min-width="160" />
              <template #empty>
                <el-empty description="暂无预约记录" :image-size="70" />
              </template>
            </el-table>
          </section>

          <section class="detail-section">
            <h3>最近报修</h3>
            <el-table :data="detail.repairs || []" size="small">
              <el-table-column prop="orderNo" label="工单号" min-width="160" />
              <el-table-column prop="issueType" label="故障类型" width="110" />
              <el-table-column prop="status" label="状态" width="100" />
              <el-table-column prop="createdAt" label="创建时间" min-width="160" />
              <template #empty>
                <el-empty description="暂无报修记录" :image-size="70" />
              </template>
            </el-table>
          </section>

          <section class="detail-section">
            <h3>违规记录</h3>
            <el-table :data="detail.violationRecords || []" size="small">
              <el-table-column prop="source" label="来源" width="120" />
              <el-table-column prop="reason" label="原因" min-width="160" />
              <el-table-column prop="detail" label="详情" min-width="220" show-overflow-tooltip />
              <el-table-column prop="happenedAt" label="发生时间" min-width="150" />
              <template #empty>
                <el-empty description="暂无违规记录" :image-size="70" />
              </template>
            </el-table>
          </section>
          <section class="detail-section">
            <div class="detail-section-head">
              <h3>通用权限</h3>
              <el-button size="small" :loading="permissionLoading" @click="refreshDetailPermissions">刷新</el-button>
            </div>
            <el-table :data="detailPermissionRows" size="small">
              <el-table-column prop="permissionCode" label="权限码" min-width="220" />
              <el-table-column label="状态" width="140">
                <template #default="{ row }">
                  <el-tag size="small" :type="permissionTagType(row)">{{ permissionStatusLabel(row) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="来源" width="140">
                <template #default="{ row }">
                  {{ permissionSourceLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column label="过期时间" min-width="180">
                <template #default="{ row }">
                  {{ row.expiresAt || (row.granted ? "长期有效" : "-") }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    :disabled="!canGrantAiPermission(detail?.user)"
                    :loading="permissionLoading"
                    @click="handleGrantPermission(row.permissionCode)"
                  >
                    授权
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    :disabled="!canRevokeAiPermission(detail?.user, row)"
                    :loading="permissionLoading"
                    @click="handleRevokePermission(row.permissionCode)"
                  >
                    撤销
                  </el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无通用权限信息" :image-size="70" />
              </template>
            </el-table>
            <p class="detail-tip">当前页面仅开放 `asset.read_basic` 的查看、授权与撤销。</p>
          </section>
        </template>

        <el-empty v-else description="暂无用户详情" />
      </div>
    </el-drawer>

    <el-dialog v-model="createVisible" title="新增用户" width="720px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="createForm.role" style="width: 100%">
                <el-option label="学生" value="student" />
                <el-option label="教师" value="teacher" />
                <el-option label="管理员" value="admin" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="账号">
              <el-input v-model.trim="createForm.username" placeholder="学生建议填写学号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="createForm.role === 'student' ? '初始密码（留空则等于学号）' : '初始密码（留空用系统默认密码）'">
              <el-input v-model.trim="createForm.password" type="password" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="昵称">
              <el-input v-model.trim="createForm.nickname" placeholder="可选" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model.trim="createForm.phone" placeholder="可选" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="createForm.role === 'student'">
            <el-form-item label="班级">
              <el-input v-model.trim="createForm.className" placeholder="如：计科2301" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="createForm.role === 'student'">
            <el-form-item label="毕业年份">
              <el-input-number v-model="createForm.graduationYear" :min="2000" :max="2200" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreateUser">创建用户</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchVisible" title="批量生成学生账号" width="820px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="学号前缀">
              <el-input v-model.trim="batchForm.prefix" placeholder="如：202301" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级">
              <el-input v-model.trim="batchForm.className" placeholder="如：计科2301" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="起始序号">
              <el-input-number v-model="batchForm.startNo" :min="1" :max="99999999" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="生成人数">
              <el-input-number v-model="batchForm.count" :min="1" :max="500" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="序号位数">
              <el-input-number v-model="batchForm.numberWidth" :min="1" :max="16" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="毕业年份">
              <el-input-number v-model="batchForm.graduationYear" :min="2000" :max="2200" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="已存在账号处理">
              <el-switch v-model="batchForm.updateIfExists" />
              <span class="switch-hint">{{ batchForm.updateIfExists ? '覆盖已有账号信息' : '跳过已有账号' }}</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="dialog-actions">
        <el-button :loading="batchPreviewLoading" @click="previewBatchStudents">预览账号</el-button>
        <el-button type="primary" :loading="batchSubmitLoading" @click="submitBatchStudents">确认生成</el-button>
      </div>

      <div class="preview-box" v-if="batchPreviewRows.length">
        <div class="preview-head">
          <strong>预览结果</strong>
          <span>共 {{ batchPreviewRows.length }} 个账号，初始密码均为学号</span>
        </div>
        <el-table :data="batchPreviewRows" max-height="320" size="small">
          <el-table-column prop="username" label="账号" min-width="140" />
          <el-table-column prop="password" label="初始密码" min-width="140" />
          <el-table-column prop="className" label="班级" min-width="140" />
          <el-table-column prop="graduationYear" label="毕业年份" width="110" />
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="importVisible" title="文本导入用户" width="780px">
      <el-form label-position="top">
        <el-form-item label="默认密码（留空使用系统默认密码）">
          <el-input v-model.trim="importForm.defaultPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="已存在账号处理">
          <el-switch v-model="importForm.updateIfExists" />
          <span class="switch-hint">{{ importForm.updateIfExists ? '覆盖已有账号信息' : '跳过已有账号' }}</span>
        </el-form-item>
        <el-form-item label="导入内容">
          <el-input
            v-model="importForm.text"
            type="textarea"
            :rows="10"
            placeholder="每行一个用户：username,password,role,className,graduationYear,nickname,phone"
          />
        </el-form-item>
      </el-form>

      <div class="dialog-hint">
        示例：`20230001,20230001,student,计科2301,2027,张三,13800000000`
      </div>

      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importLoading" @click="submitImportUsers">执行导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="graduateVisible" title="毕业生批量停用" width="720px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="毕业年份">
              <el-input-number v-model="graduateForm.graduationYear" :min="2000" :max="2200" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级关键字">
              <el-input v-model.trim="graduateForm.classKeyword" placeholder="可选，如：计科2301" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="停用范围">
              <el-radio-group v-model="graduateForm.mode">
                <el-radio label="eq">仅该届</el-radio>
                <el-radio label="lte">该届及以前</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="dialog-actions">
        <el-button :loading="graduatePreviewLoading" @click="previewGraduateDeactivate">预览命中</el-button>
        <el-button type="danger" :loading="graduateSubmitLoading" @click="submitGraduateDeactivate">确认停用</el-button>
      </div>

      <div class="preview-box" v-if="graduatePreviewRows.length">
        <div class="preview-head">
          <strong>命中用户</strong>
          <span>共 {{ graduatePreviewMatched }} 人</span>
        </div>
        <el-table :data="graduatePreviewRows" max-height="320" size="small">
          <el-table-column prop="username" label="账号" min-width="140" />
          <el-table-column prop="className" label="班级" min-width="140" />
          <el-table-column prop="graduationYear" label="毕业年份" width="110" />
          <el-table-column label="当前状态" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="row.isActive ? 'success' : 'info'">
                {{ row.isActive ? '正常' : '已停用' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeactivateGraduates,
  batchGenerateStudents,
  createUser,
  deleteUser,
  freezeUser,
  getUserAiPermissions,
  getUserDetail,
  getUserPermissions,
  getUserGovernanceStats,
  getUsers,
  grantUserAiPermission,
  grantUserPermission,
  importUsers,
  resetUserPassword,
  revokeUserAiPermission,
  revokeUserPermission,
  setUserRole,
  unfreezeUser
} from '@/api/users'

const AI_RESERVATION_VIEW_OWNER = 'ai.reservation.view_owner'
const PERMISSION_ASSET_READ_BASIC = 'asset.read_basic'

const loading = ref(false)
const detailLoading = ref(false)
const aiPermissionLoading = ref(false)
const permissionLoading = ref(false)
const createLoading = ref(false)
const batchPreviewLoading = ref(false)
const batchSubmitLoading = ref(false)
const importLoading = ref(false)
const graduatePreviewLoading = ref(false)
const graduateSubmitLoading = ref(false)

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const detailVisible = ref(false)
const detail = ref(null)

const createVisible = ref(false)
const batchVisible = ref(false)
const importVisible = ref(false)
const graduateVisible = ref(false)

const batchPreviewRows = ref([])
const graduatePreviewRows = ref([])
const graduatePreviewMatched = ref(0)
const governanceStats = ref({
  total: 0,
  adminCount: 0,
  teacherCount: 0,
  studentCount: 0,
  neverLoginStudentCount: 0,
  graduatePendingDeactivateCount: 0,
  violationUnfrozenCount: 0,
  missingClassNameCount: 0,
  missingGraduationYearCount: 0
})

const filters = reactive({
  keyword: '',
  role: '',
  className: '',
  graduationYear: undefined,
  activeState: 'all',
  graduateReferenceYear: new Date().getFullYear(),
  quickFilter: 'all',
  neverLoggedIn: 'all',
  hasViolation: 'all',
  loginDays: 'all'
})

const quickFilterOptions = [
  { label: '全部用户', value: 'all' },
  { label: '从未登录学生', value: 'never-login-student' },
  { label: '已毕业未停用', value: 'graduate-pending' },
  { label: '有违规未冻结', value: 'violation-unfrozen' },
  { label: '学生缺少班级', value: 'missing-class' },
  { label: '学生缺少毕业年份', value: 'missing-graduation' }
]

const quickFilterDescriptions = {
  'never-login-student': '仅查看从未登录过的学生账号，适合排查新建后未启用的账号。',
  'graduate-pending': '仅查看已到毕业年份但仍处于启用状态的学生账号。',
  'violation-unfrozen': '仅查看已有违规记录但尚未冻结的账号，便于快速干预。',
  'missing-class': '仅查看班级信息为空的学生账号，用于治理历史脏数据。',
  'missing-graduation': '仅查看毕业年份缺失的学生账号，便于后续毕业停用治理。'
}

const activeQuickFilterMeta = computed(() => {
  if (filters.quickFilter === 'all') {
    return null
  }
  const target = quickFilterOptions.find((item) => item.value === filters.quickFilter)
  if (!target) {
    return null
  }
  return {
    ...target,
    description:
      filters.quickFilter === 'graduate-pending'
        ? `仅查看毕业年份小于等于 ${filters.graduateReferenceYear} 且仍处于启用状态的学生账号。`
        : quickFilterDescriptions[filters.quickFilter] || ''
  }
})

const createForm = reactive({
  role: 'student',
  username: '',
  password: '',
  nickname: '',
  phone: '',
  className: '',
  graduationYear: new Date().getFullYear() + 4
})

const batchForm = reactive({
  prefix: '',
  className: '',
  startNo: 1,
  count: 40,
  numberWidth: 2,
  graduationYear: new Date().getFullYear() + 4,
  updateIfExists: false
})

const importForm = reactive({
  defaultPassword: '',
  updateIfExists: true,
  text: ''
})

const graduateForm = reactive({
  graduationYear: new Date().getFullYear(),
  classKeyword: '',
  mode: 'eq'
})

const pageRoleSummary = computed(() => rows.value.reduce((acc, item) => {
  const role = item.role || 'student'
  acc[role] = (acc[role] || 0) + 1
  return acc
}, { admin: 0, teacher: 0, student: 0 }))

const governanceCards = computed(() => [
  { label: '从未登录学生', value: governanceStats.value.neverLoginStudentCount || 0, quickFilter: 'never-login-student' },
  { label: '已毕业未停用', value: governanceStats.value.graduatePendingDeactivateCount || 0, quickFilter: 'graduate-pending' },
  { label: '有违规未冻结', value: governanceStats.value.violationUnfrozenCount || 0, quickFilter: 'violation-unfrozen' },
  { label: '学生缺少班级', value: governanceStats.value.missingClassNameCount || 0, quickFilter: 'missing-class' },
  { label: '学生缺少毕业年份', value: governanceStats.value.missingGraduationYearCount || 0, quickFilter: 'missing-graduation' }
])

const detailAiPermissionRows = computed(() => {
  const items = Array.isArray(detail.value?.aiPermissions) ? detail.value.aiPermissions : []
  return items.filter((item) => item.permissionCode === AI_RESERVATION_VIEW_OWNER)
})

const detailPermissionRows = computed(() => {
  const items = Array.isArray(detail.value?.permissions) ? detail.value.permissions : []
  return items.filter((item) => item.permissionCode === PERMISSION_ASSET_READ_BASIC)
})

function resetCreateForm() {
  createForm.role = 'student'
  createForm.username = ''
  createForm.password = ''
  createForm.nickname = ''
  createForm.phone = ''
  createForm.className = ''
  createForm.graduationYear = new Date().getFullYear() + 4
}

function resetBatchForm() {
  batchForm.prefix = ''
  batchForm.className = ''
  batchForm.startNo = 1
  batchForm.count = 40
  batchForm.numberWidth = 2
  batchForm.graduationYear = new Date().getFullYear() + 4
  batchForm.updateIfExists = false
  batchPreviewRows.value = []
}

function resetImportForm() {
  importForm.defaultPassword = ''
  importForm.updateIfExists = true
  importForm.text = ''
}

function resetGraduateForm() {
  graduateForm.graduationYear = new Date().getFullYear()
  graduateForm.classKeyword = ''
  graduateForm.mode = 'eq'
  graduatePreviewRows.value = []
  graduatePreviewMatched.value = 0
}

function buildQueryParams() {
  const params = {
    page: page.value,
    pageSize: pageSize.value,
    keyword: filters.keyword,
    role: filters.role,
    className: filters.className
  }

  if (filters.graduationYear) {
    params.graduationYear = filters.graduationYear
  }

  if (filters.activeState === 'active') {
    params.isActive = 1
    params.isFrozen = 0
  } else if (filters.activeState === 'inactive') {
    params.isActive = 0
  } else if (filters.activeState === 'frozen') {
    params.isFrozen = 1
  }

  if (filters.hasViolation === 'yes') {
    params.hasViolation = 1
  } else if (filters.hasViolation === 'no') {
    params.hasViolation = 0
  }

  if (filters.neverLoggedIn === 'yes') {
    params.neverLoggedIn = 1
  } else if (filters.neverLoggedIn === 'no') {
    params.neverLoggedIn = 0
  }

  if (filters.loginDays !== 'all') {
    params.loginDays = filters.loginDays
  }

  if (filters.quickFilter === 'never-login-student') {
    params.role = 'student'
    params.neverLoggedIn = 1
  } else if (filters.quickFilter === 'graduate-pending') {
    params.graduatePendingDeactivate = 1
    params.graduateReferenceYear = filters.graduateReferenceYear
  } else if (filters.quickFilter === 'violation-unfrozen') {
    params.violationUnfrozen = 1
  } else if (filters.quickFilter === 'missing-class') {
    params.missingClassName = 1
  } else if (filters.quickFilter === 'missing-graduation') {
    params.missingGraduationYear = 1
  }

  return params
}

function applyQuickFilter(value) {
  filters.quickFilter = value
  handleSearch()
}

function handleSearch() {
  page.value = 1
  fetchRows()
}

async function fetchRows() {
  loading.value = true
  try {
    const response = await getUsers(buildQueryParams())
    rows.value = (response.data?.data || []).map((item) => ({
      ...item,
      _originalRole: item.role
    }))
    total.value = response.data?.meta?.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchGovernanceStats() {
  const response = await getUserGovernanceStats({
    graduateReferenceYear: filters.graduateReferenceYear
  })
  governanceStats.value = {
    ...governanceStats.value,
    ...(response.data?.data || {})
  }
}

function handleGraduateReferenceYearChange() {
  fetchGovernanceStats()
  if (filters.quickFilter === 'graduate-pending') {
    handleSearch()
  }
}

async function refreshUserView() {
  await Promise.all([fetchRows(), fetchGovernanceStats()])
}

function resetFilters() {
  filters.keyword = ''
  filters.role = ''
  filters.className = ''
  filters.graduationYear = undefined
  filters.activeState = 'all'
  filters.graduateReferenceYear = new Date().getFullYear()
  filters.quickFilter = 'all'
  filters.neverLoggedIn = 'all'
  filters.hasViolation = 'all'
  filters.loginDays = 'all'
  refreshUserView()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  page.value = 1
  fetchRows()
}

async function changeRole(row) {
  const nextRole = row.role
  const previousRole = row._originalRole || row.role
  try {
    await setUserRole(row.id, { role: nextRole })
    row._originalRole = nextRole
    ElMessage.success('角色已更新')
    await refreshUserView()
  } catch (error) {
    row.role = previousRole
    throw error
  }
}

async function toggleFreeze(row) {
  if (row.isFrozen) {
    await unfreezeUser(row.id)
    ElMessage.success('用户已解冻')
  } else {
    await freezeUser(row.id)
    ElMessage.success('用户已冻结')
  }
  await refreshUserView()
}

async function handleResetPassword(row) {
  await ElMessageBox.confirm(`确认重置用户 ${row.username} 的密码吗？`, '重置密码', { type: 'warning' })
  const response = await resetUserPassword(row.id)
  const temporaryPassword = response.data?.data?.temporaryPassword || ''
  if (temporaryPassword) {
    await ElMessageBox.alert(`临时密码：${temporaryPassword}`, '密码已重置', { confirmButtonText: '知道了' })
  } else {
    ElMessage.success('密码已重置')
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除用户 ${row.username} 吗？`, '删除用户', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('用户已删除')
  await refreshUserView()
}

async function viewDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const response = await getUserDetail(row.id, { limit: 20 })
    detail.value = response.data?.data || null
    await Promise.all([refreshDetailAiPermissions(), refreshDetailPermissions()])
  } finally {
    detailLoading.value = false
  }
}

function aiPermissionStatusLabel(row) {
  if (row?.granted) {
    return row?.source === 'role_default' ? '默认拥有' : '已授权'
  }
  if (row?.source === 'expired') {
    return '已过期'
  }
  return '未授权'
}

function aiPermissionTagType(row) {
  if (row?.granted) return 'success'
  if (row?.source === 'expired') return 'warning'
  return 'info'
}

function aiPermissionSourceLabel(row) {
  if (row?.source === 'role_default') return '角色默认'
  if (row?.source === 'user_grant') return '管理员授权'
  if (row?.source === 'expired') return '授权已过期'
  return '未授权'
}

function permissionStatusLabel(row) {
  if (row?.granted) {
    return row?.source === 'role_default' ? '默认拥有' : '已授权'
  }
  if (row?.source === 'expired') {
    return '已过期'
  }
  return '未授权'
}

function permissionTagType(row) {
  if (row?.granted) return 'success'
  if (row?.source === 'expired') return 'warning'
  return 'info'
}

function permissionSourceLabel(row) {
  if (row?.source === 'role_default') return '角色默认'
  if (row?.source === 'user_grant') return '管理员授权'
  if (row?.source === 'expired') return '授权过期'
  return '未授权'
}

function canGrantAiPermission(user) {
  const role = String(user?.role || '').trim()
  return role === 'teacher' || role === 'student'
}

function canRevokeAiPermission(user, row) {
  if (!canGrantAiPermission(user)) return false
  return !!row?.granted || row?.source === 'expired'
}

async function refreshDetailAiPermissions() {
  const userId = Number(detail.value?.user?.id || 0)
  if (!userId) return
  aiPermissionLoading.value = true
  try {
    const response = await getUserAiPermissions(userId)
    const items = response.data?.data?.items || []
    if (!detail.value) detail.value = {}
    detail.value = {
      ...detail.value,
      aiPermissions: Array.isArray(items) ? items : []
    }
  } finally {
    aiPermissionLoading.value = false
  }
}

async function refreshDetailPermissions() {
  const userId = Number(detail.value?.user?.id || 0)
  if (!userId) return
  permissionLoading.value = true
  try {
    const response = await getUserPermissions(userId)
    const items = response.data?.data?.items || []
    if (!detail.value) detail.value = {}
    detail.value = {
      ...detail.value,
      permissions: Array.isArray(items) ? items : []
    }
  } finally {
    permissionLoading.value = false
  }
}

async function handleGrantAiPermission(permissionCode) {
  const user = detail.value?.user || {}
  if (!canGrantAiPermission(user)) {
    ElMessage.warning('仅支持给教师或学生授权')
    return
  }
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '可留空表示长期有效；如需设置过期时间，请输入 YYYY-MM-DD HH:mm:ss。',
      '授权 AI 权限',
      {
        confirmButtonText: '授权',
        cancelButtonText: '取消',
        inputValue: '',
        inputPlaceholder: '例如：2026-03-31 23:59:59',
        inputPattern: /^$|^\d{4}-\d{2}-\d{2}(?:\s|T)\d{2}:\d{2}:\d{2}$/,
        inputErrorMessage: '请输入 YYYY-MM-DD HH:mm:ss，或留空'
      }
    )
  } catch (error) {
    return
  }
  aiPermissionLoading.value = true
  try {
    const expiresAt = String(promptResult?.value || '').trim()
    await grantUserAiPermission(user.id, {
      permissionCode,
      expiresAt: expiresAt || undefined
    })
    await refreshDetailAiPermissions()
    ElMessage.success('AI 权限已授权')
  } finally {
    aiPermissionLoading.value = false
  }
}

async function handleRevokeAiPermission(permissionCode) {
  const user = detail.value?.user || {}
  if (!canGrantAiPermission(user)) {
    ElMessage.warning('仅支持撤销教师或学生的 AI 权限')
    return
  }
  await ElMessageBox.confirm('确认撤销该用户的 AI 权限吗？', '撤销 AI 权限', { type: 'warning' })
  aiPermissionLoading.value = true
  try {
    await revokeUserAiPermission(user.id, { permissionCode })
    await refreshDetailAiPermissions()
    ElMessage.success('AI 权限已撤销')
  } finally {
    aiPermissionLoading.value = false
  }
}

async function handleGrantPermission(permissionCode) {
  const user = detail.value?.user || {}
  if (!canGrantAiPermission(user)) {
    ElMessage.warning('浠呮敮鎸佺粰鏁欏笀鎴栧鐢熸巿鏉?')
    return
  }
  let promptResult
  try {
    promptResult = await ElMessageBox.prompt(
      '鍙暀绌鸿〃绀洪暱鏈熸湁鏁堬紱濡傞渶璁剧疆杩囨湡鏃堕棿锛岃杈撳叆 YYYY-MM-DD HH:mm:ss銆?',
      '鎺堟潈閫氱敤鏉冮檺',
      {
        confirmButtonText: '鎺堟潈',
        cancelButtonText: '鍙栨秷',
        inputValue: '',
        inputPlaceholder: '渚嬪锛?026-03-31 23:59:59',
        inputPattern: /^$|^\d{4}-\d{2}-\d{2}(?:\s|T)\d{2}:\d{2}:\d{2}$/,
        inputErrorMessage: '璇疯緭鍏?YYYY-MM-DD HH:mm:ss锛屾垨鐣欑┖'
      }
    )
  } catch (error) {
    return
  }
  permissionLoading.value = true
  try {
    const expiresAt = String(promptResult?.value || '').trim()
    await grantUserPermission(user.id, {
      permissionCode,
      expiresAt: expiresAt || undefined
    })
    await refreshDetailPermissions()
    ElMessage.success('閫氱敤鏉冮檺宸叉巿鏉?')
  } finally {
    permissionLoading.value = false
  }
}

async function handleRevokePermission(permissionCode) {
  const user = detail.value?.user || {}
  if (!canGrantAiPermission(user)) {
    ElMessage.warning('浠呮敮鎸佹挙閿€鏁欏笀鎴栧鐢熺殑閫氱敤鏉冮檺')
    return
  }
  await ElMessageBox.confirm('纭鎾ら攢璇ョ敤鎴风殑閫氱敤鏉冮檺鍚楋紵', '鎾ら攢閫氱敤鏉冮檺', { type: 'warning' })
  permissionLoading.value = true
  try {
    await revokeUserPermission(user.id, { permissionCode })
    await refreshDetailPermissions()
    ElMessage.success('閫氱敤鏉冮檺宸叉挙閿€')
  } finally {
    permissionLoading.value = false
  }
}

function openCreateDialog() {
  resetCreateForm()
  createVisible.value = true
}

function openBatchDialog() {
  resetBatchForm()
  batchVisible.value = true
}

function openImportDialog() {
  resetImportForm()
  importVisible.value = true
}

function openGraduateDialog() {
  resetGraduateForm()
  graduateVisible.value = true
}

function validateCreateForm() {
  if (!createForm.username.trim()) {
    ElMessage.warning('请填写账号')
    return false
  }
  if (createForm.password.trim() && createForm.password.trim().length < 6) {
    ElMessage.warning('密码长度不能少于 6 位')
    return false
  }
  if (createForm.role === 'student') {
    if (!createForm.className.trim()) {
      ElMessage.warning('学生必须填写班级')
      return false
    }
    if (!createForm.graduationYear) {
      ElMessage.warning('学生必须填写毕业年份')
      return false
    }
  }
  return true
}

async function submitCreateUser() {
  if (!validateCreateForm()) return

  const payload = {
    username: createForm.username.trim(),
    role: createForm.role,
    password: createForm.password.trim(),
    nickname: createForm.nickname.trim(),
    phone: createForm.phone.trim(),
    className: createForm.role === 'student' ? createForm.className.trim() : '',
    graduationYear: createForm.role === 'student' ? createForm.graduationYear : 0
  }

  createLoading.value = true
  try {
    const response = await createUser(payload)
    const initialPassword = response.data?.data?.initialPassword || ''
    createVisible.value = false
    await refreshUserView()
    await ElMessageBox.alert(
      `账号创建成功。\n账号：${payload.username}\n初始密码：${initialPassword || '系统默认密码'}`,
      '创建成功',
      { confirmButtonText: '知道了' }
    )
  } finally {
    createLoading.value = false
  }
}

function validateBatchForm() {
  if (!batchForm.prefix.trim()) {
    ElMessage.warning('请填写学号前缀')
    return false
  }
  if (!batchForm.className.trim()) {
    ElMessage.warning('请填写班级')
    return false
  }
  if (!batchForm.count || batchForm.count <= 0) {
    ElMessage.warning('请填写生成人数')
    return false
  }
  return true
}

function buildBatchPayload(dryRun) {
  return {
    prefix: batchForm.prefix.trim(),
    className: batchForm.className.trim(),
    startNo: batchForm.startNo,
    count: batchForm.count,
    numberWidth: batchForm.numberWidth,
    graduationYear: batchForm.graduationYear,
    updateIfExists: batchForm.updateIfExists,
    dryRun
  }
}

async function previewBatchStudents() {
  if (!validateBatchForm()) return
  batchPreviewLoading.value = true
  try {
    const response = await batchGenerateStudents(buildBatchPayload(true))
    batchPreviewRows.value = response.data?.data?.preview || []
  } finally {
    batchPreviewLoading.value = false
  }
}

async function submitBatchStudents() {
  if (!validateBatchForm()) return
  batchSubmitLoading.value = true
  try {
    const response = await batchGenerateStudents(buildBatchPayload(false))
    const data = response.data?.data || {}
    batchVisible.value = false
    await refreshUserView()
    ElMessage.success(`批量生成完成：新增 ${data.inserted || 0}，更新 ${data.updated || 0}，跳过 ${data.skipped || 0}，失败 ${data.failed || 0}`)
  } finally {
    batchSubmitLoading.value = false
  }
}

async function submitImportUsers() {
  if (!importForm.text.trim()) {
    ElMessage.warning('请先输入导入内容')
    return
  }

  importLoading.value = true
  try {
    const response = await importUsers({
      text: importForm.text.trim(),
      updateIfExists: importForm.updateIfExists,
      defaultPassword: importForm.defaultPassword.trim() || undefined
    })
    const data = response.data?.data || {}
    importVisible.value = false
    await refreshUserView()
    ElMessage.success(`导入完成：新增 ${data.inserted || 0}，更新 ${data.updated || 0}，跳过 ${data.skipped || 0}，失败 ${data.failed || 0}`)
  } finally {
    importLoading.value = false
  }
}

async function previewGraduateDeactivate() {
  graduatePreviewLoading.value = true
  try {
    const response = await batchDeactivateGraduates({
      graduationYear: graduateForm.graduationYear,
      classKeyword: graduateForm.classKeyword.trim(),
      mode: graduateForm.mode,
      dryRun: true
    })
    const data = response.data?.data || {}
    graduatePreviewRows.value = data.preview || []
    graduatePreviewMatched.value = data.matched || 0
  } finally {
    graduatePreviewLoading.value = false
  }
}

async function submitGraduateDeactivate() {
  await ElMessageBox.confirm('确认停用命中的毕业生账号吗？该操作会撤销他们的刷新令牌。', '毕业生停用', {
    type: 'warning'
  })
  graduateSubmitLoading.value = true
  try {
    const response = await batchDeactivateGraduates({
      graduationYear: graduateForm.graduationYear,
      classKeyword: graduateForm.classKeyword.trim(),
      mode: graduateForm.mode,
      dryRun: false
    })
    const data = response.data?.data || {}
    graduateVisible.value = false
    await refreshUserView()
    ElMessage.success(`已停用 ${data.deactivated || 0} 个账号`)
  } finally {
    graduateSubmitLoading.value = false
  }
}

onMounted(() => {
  refreshUserView()
})
</script>

<style scoped lang="scss">
.page-wrap {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head,
.page-card {
  padding: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  box-shadow: var(--app-shadow);
}

.page-head {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 36%),
    linear-gradient(135deg, #ffffff, #f5fbfa);
}

.page-head::after {
  content: '';
  position: absolute;
  right: -36px;
  bottom: -84px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 212, 191, 0.18), rgba(45, 212, 191, 0));
}

.page-card {
  background: var(--app-surface);
}

.page-head,
.head-actions,
.pager-row,
.dialog-actions,
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.head-actions {
  position: relative;
  z-index: 1;
  flex-wrap: wrap;
}

.page-head h2 {
  margin: 8px 0 10px;
  font-size: 30px;
}

.page-head p,
.switch-hint,
.dialog-hint {
  margin: 0;
  color: var(--app-muted);
  line-height: 1.7;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.filter-form {
  margin-bottom: 16px;
}

.quick-filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.quick-filter-label {
  color: var(--app-muted);
  font-size: 13px;
}

.governance-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.governance-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.governance-card {
  padding: 16px;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.governance-card span {
  display: block;
  color: var(--app-muted);
  margin-bottom: 8px;
}

.governance-card strong {
  font-size: 24px;
  color: #0f172a;
}

.governance-card:hover,
.governance-card.active {
  border-color: var(--el-color-primary);
  background: #ecfeff;
}

.quick-filter-hint {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.quick-filter-hint strong {
  display: block;
  margin-bottom: 6px;
}

.quick-filter-hint p {
  margin: 0;
  color: var(--app-muted);
  line-height: 1.6;
}

.summary-grid,
.detail-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-grid {
  margin-bottom: 18px;
}

.summary-card {
  padding: 16px;
  border-radius: 16px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card span {
  color: var(--app-muted);
}

.summary-card strong {
  font-size: 24px;
}

.pager-row {
  margin-top: 18px;
  justify-content: flex-end;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section h3 {
  margin: 0 0 12px;
}

.detail-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-tip {
  margin: 12px 0 0;
  color: var(--app-muted);
  font-size: 13px;
}

.dialog-actions {
  margin-bottom: 12px;
}

.preview-box {
  border: 1px solid var(--app-border);
  border-radius: 18px;
  padding: 16px;
  background: #f8fafc;
}

.preview-head {
  margin-bottom: 12px;
}

.preview-head span {
  color: var(--app-muted);
  font-size: 13px;
}

.switch-hint {
  margin-left: 12px;
  font-size: 13px;
}

.dialog-hint {
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .governance-grid,
  .summary-grid,
  .detail-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .page-head,
  .head-actions,
  .preview-head,
  .quick-filter-row,
  .quick-filter-hint,
  .governance-toolbar,
  .detail-section-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
