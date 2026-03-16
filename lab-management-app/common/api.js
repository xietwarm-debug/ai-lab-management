const envBaseUrl =
  (typeof process !== "undefined" && process.env && process.env.UNI_APP_BASE_URL) || "";
const normalizedEnvBaseUrl = String(envBaseUrl || "").trim().replace(/\/+$/, "");
const isProduction =
  typeof process !== "undefined" && process.env && process.env.NODE_ENV === "production";
const DEFAULT_DEV_BASE_URL = "http://127.0.0.1:5000";

export const BASE_URL = normalizedEnvBaseUrl || (isProduction ? "" : DEFAULT_DEV_BASE_URL);
export function buildApiUrl(path) {
  const raw = String(path || "").trim();
  if (!raw) return BASE_URL;
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith("/")) return `${BASE_URL}${raw}`;
  return `${BASE_URL}/${raw}`;
}

export function toQuery(params) {
  const pairs = [];
  Object.keys(params || {}).forEach((k) => {
    const key = String(k || "").trim();
    const value = (params || {})[k];
    if (!key || value === undefined || value === null || value === "") return;
    pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  });
  return pairs.join("&");
}

export function getApiData(payload) {
  if (
    payload &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    Object.prototype.hasOwnProperty.call(payload, "data")
  ) {
    return payload.data;
  }
  return payload;
}

export function getApiListData(payload) {
  const data = getApiData(payload);
  return Array.isArray(data) ? data : [];
}

export function getApiMeta(payload) {
  if (payload && typeof payload === "object" && !Array.isArray(payload) && payload.meta && typeof payload.meta === "object") {
    return payload.meta;
  }
  return {};
}

export function sleep(ms = 0) {
  const duration = Number(ms || 0);
  return new Promise((resolve) => {
    setTimeout(resolve, duration > 0 ? duration : 0);
  });
}

export async function requestWithRetry(requester, options = {}) {
  const fn = typeof requester === "function" ? requester : null;
  if (!fn) throw new Error("requester must be a function");

  const retries = Math.max(0, Number((options || {}).retries || 0));
  const delayMs = Math.max(0, Number((options || {}).delayMs || 0));
  let lastError = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fn(attempt);
    } catch (error) {
      lastError = error;
      if (attempt >= retries) break;
      if (delayMs > 0) {
        await sleep(delayMs);
      }
    }
  }

  throw lastError || new Error("request failed");
}

export function readStorageCache(key, options = {}) {
  const cacheKey = String(key || "").trim();
  if (!cacheKey) return null;

  const maxAgeMs = Math.max(0, Number((options || {}).maxAgeMs || 0));
  try {
    const raw = uni.getStorageSync(cacheKey);
    const payload = raw && typeof raw === "object" ? raw : null;
    if (!payload || !Object.prototype.hasOwnProperty.call(payload, "data")) return null;

    const storedAt = Number(payload.storedAt || 0);
    if (maxAgeMs > 0 && storedAt > 0 && Date.now() - storedAt > maxAgeMs) {
      return null;
    }
    return payload.data;
  } catch (e) {
    return null;
  }
}

export function writeStorageCache(key, data) {
  const cacheKey = String(key || "").trim();
  if (!cacheKey) return data;

  try {
    uni.setStorageSync(cacheKey, {
      storedAt: Date.now(),
      data
    });
  } catch (e) {}
  return data;
}

export async function apiRequest(options = {}) {
  const {
    url = "",
    method = "GET",
    data = undefined,
    header = {},
  } = options || {};
  const finalUrl = buildApiUrl(url);
  const res = await uni.request({
    url: finalUrl,
    method: String(method || "GET").toUpperCase(),
    data,
    header,
  });
  return res || {};
}

export async function submitUserFeedback(payload = {}) {
  return apiRequest({
    url: "/feedback",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherCreateCourse(payload = {}) {
  return apiRequest({
    url: "/teacher/courses",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherUpdateCourse(courseId, payload = {}) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherDeleteCourse(courseId) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/delete`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherListCourses(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/teacher/courses${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function listCourses(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/courses${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function listLabs(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/labs${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function listAnnouncements(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/announcements${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function teacherCreateCourseTask(courseId, payload = {}) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/tasks`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function listCourseTasks(courseId) {
  return apiRequest({
    url: `/courses/${encodeURIComponent(String(courseId || ""))}/tasks`,
    method: "GET"
  });
}

export async function listTaskFiles(taskId) {
  return apiRequest({
    url: `/tasks/${encodeURIComponent(String(taskId || ""))}/files`,
    method: "GET"
  });
}

export async function teacherListTaskStudentFiles(taskId) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/student-files`,
    method: "GET"
  });
}

export async function teacherListHomeworkReviews(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/teacher/homework-reviews${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function teacherReviewTaskStudentFile(fileId, payload = {}) {
  return apiRequest({
    url: `/teacher/student-files/${encodeURIComponent(String(fileId || ""))}/review`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherGetAiReviewSuggestion(fileId) {
  return apiRequest({
    url: `/teacher/student-files/${encodeURIComponent(String(fileId || ""))}/ai-review-suggestion`,
    method: "GET"
  });
}

export async function teacherBatchGetAiReviewSuggestions(fileIds = []) {
  return apiRequest({
    url: "/teacher/student-files/ai-review-suggestions",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {
      fileIds: Array.isArray(fileIds) ? fileIds : []
    }
  });
}

export async function teacherGetTaskReservePlans(taskId, payload = {}) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/ai-reserve-plan`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherGetTaskNoticeDraft(taskId, payload = {}) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/ai-notice-draft`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export function teacherHomeworkReviewExportUrl(params = {}) {
  const query = toQuery(params || {});
  return buildApiUrl(`/teacher/homework-reviews/export${query ? `?${query}` : ""}`);
}

export async function listTaskStudentFiles(taskId) {
  return apiRequest({
    url: `/tasks/${encodeURIComponent(String(taskId || ""))}/student-files`,
    method: "GET"
  });
}

export async function teacherDeleteTaskStudentFile(fileId) {
  return apiRequest({
    url: `/teacher/student-files/${encodeURIComponent(String(fileId || ""))}/delete`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function uploadTaskStudentFile(taskId, filePath, formData = {}) {
  return uni.uploadFile({
    url: buildApiUrl(`/tasks/${encodeURIComponent(String(taskId || ""))}/student-files/upload`),
    filePath: String(filePath || ""),
    name: "file",
    formData: formData || {}
  });
}

export async function submitTaskStudentText(taskId, payload = {}) {
  return apiRequest({
    url: `/tasks/${encodeURIComponent(String(taskId || ""))}/student-files/upload`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherUploadTaskFile(taskId, filePath) {
  return uni.uploadFile({
    url: buildApiUrl(`/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/files/upload`),
    filePath: String(filePath || ""),
    name: "file"
  });
}

export async function teacherDeleteTaskFile(fileId) {
  return apiRequest({
    url: `/teacher/task-files/${encodeURIComponent(String(fileId || ""))}/delete`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherDeleteTask(taskId) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/delete`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function joinCourseByCode(payload = {}) {
  return apiRequest({
    url: "/courses/join-by-code",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherListCourseStudents(courseId) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/students`,
    method: "GET"
  });
}

export async function teacherRemoveCourseStudent(courseId, studentUserName) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/students/${encodeURIComponent(String(studentUserName || ""))}/remove`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherNotifyMissingTask(courseId, taskId) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/tasks/${encodeURIComponent(String(taskId || ""))}/notify-missing`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherAutoNotifyMissingTasks(courseId) {
  return apiRequest({
    url: `/teacher/courses/${encodeURIComponent(String(courseId || ""))}/tasks/auto-notify`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherListTaskTemplates(params = {}) {
  const query = toQuery(params || {});
  return apiRequest({
    url: `/teacher/task-templates${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function studentWithdrawTaskStudentFile(fileId) {
  return apiRequest({
    url: `/tasks/student-files/${encodeURIComponent(String(fileId || ""))}/withdraw`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function getCourseTaskReminderSubscription() {
  return apiRequest({
    url: "/me/course-task-reminder-subscription",
    method: "GET"
  });
}

export async function saveCourseTaskReminderSubscription(payload = {}) {
  return apiRequest({
    url: "/me/course-task-reminder-subscription",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function changePassword(payload = {}) {
  return apiRequest({
    url: "/auth/change-password",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function getAuthSecurity(currentRefreshToken = "") {
  const query = toQuery({ currentRefreshToken: String(currentRefreshToken || "").trim() });
  return apiRequest({
    url: `/auth/security${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function bindSecurityPhone(phone) {
  return apiRequest({
    url: "/auth/bind-phone",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { phone: String(phone || "").trim() }
  });
}

export async function bindSecurityEmail(email) {
  return apiRequest({
    url: "/auth/bind-email",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { email: String(email || "").trim() }
  });
}

export async function listLoginDevices(currentRefreshToken = "") {
  const query = toQuery({ currentRefreshToken: String(currentRefreshToken || "").trim() });
  return apiRequest({
    url: `/auth/login-devices${query ? `?${query}` : ""}`,
    method: "GET"
  });
}

export async function revokeLoginDevice(deviceId, currentRefreshToken = "") {
  return apiRequest({
    url: `/auth/login-devices/${encodeURIComponent(String(deviceId || ""))}/revoke`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { currentRefreshToken: String(currentRefreshToken || "").trim() }
  });
}

export async function revokeOtherLoginDevices(currentRefreshToken = "") {
  return apiRequest({
    url: "/auth/login-devices/revoke-others",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { currentRefreshToken: String(currentRefreshToken || "").trim() }
  });
}

export async function adminListClassPeriodConfigs() {
  return apiRequest({
    url: "/admin/class-period-configs",
    method: "GET"
  });
}

export async function adminListScheduleTemplates() {
  return apiRequest({
    url: "/admin/schedule/templates",
    method: "GET"
  });
}

export async function adminGetScheduleTemplateDetail(templateId) {
  return apiRequest({
    url: `/admin/schedule/templates/${encodeURIComponent(String(templateId || ""))}`,
    method: "GET"
  });
}

export async function adminActivateScheduleTemplate(templateId) {
  return apiRequest({
    url: `/admin/schedule/templates/${encodeURIComponent(String(templateId || ""))}/activate`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminDeleteScheduleTemplate(templateId) {
  return apiRequest({
    url: `/admin/schedule/templates/${encodeURIComponent(String(templateId || ""))}/delete`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminImportSchedule(payload = {}) {
  return apiRequest({
    url: "/admin/schedule/import",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminGetDoorRemindersToday(dateText = "") {
  const q = toQuery({ date: dateText });
  return apiRequest({
    url: `/admin/door-reminders/today${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminGetDoorRemindersWeek(dateText = "") {
  const q = toQuery({ date: dateText });
  return apiRequest({
    url: `/admin/door-reminders/week${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminGetAiDailyBrief() {
  return apiRequest({
    url: "/admin/ai/daily-brief",
    method: "GET"
  });
}

export async function adminQueryStatsAi(payload = {}) {
  return apiRequest({
    url: "/admin/stats/ai-query",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminGetAiRiskAlerts() {
  return apiRequest({
    url: "/admin/ai/risk-alerts",
    method: "GET"
  });
}

export async function adminGetAiEquipmentHealth(limit = 8) {
  const q = toQuery({ limit });
  return apiRequest({
    url: `/admin/ai/equipment-health${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminRefreshAiEquipmentHealth(payload = {}) {
  return apiRequest({
    url: "/admin/ai/equipment-health/refresh",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminListKnowledgeDocuments(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/admin/knowledge/documents${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminCreateKnowledgeDocument(payload = {}) {
  return apiRequest({
    url: "/admin/knowledge/documents",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminUpdateKnowledgeDocument(documentId, payload = {}) {
  return apiRequest({
    url: `/admin/knowledge/documents/${encodeURIComponent(String(documentId || ""))}`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminUpdateKnowledgeDocumentStatus(documentId, status) {
  return apiRequest({
    url: `/admin/knowledge/documents/${encodeURIComponent(String(documentId || ""))}/status`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { status }
  });
}

export async function adminReindexKnowledgeDocument(documentId) {
  return apiRequest({
    url: `/admin/knowledge/documents/${encodeURIComponent(String(documentId || ""))}/reindex`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function askKnowledgeBase(payload = {}) {
  return apiRequest({
    url: "/knowledge/ask",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function feedbackKnowledgeBase(payload = {}) {
  return apiRequest({
    url: "/knowledge/feedback",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function getReservationAiSuggestion(reservationId) {
  return apiRequest({
    url: `/reservations/${encodeURIComponent(String(reservationId || ""))}/ai-suggestion`,
    method: "GET"
  });
}

export async function adminGenerateAnnouncementAiDraft(payload = {}) {
  return apiRequest({
    url: "/announcements/ai-draft",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminGetDoorReminderRecords(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/admin/door-reminders/records${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminConfirmDoorReminderOpen(reminderId, payload = {}) {
  return apiRequest({
    url: `/admin/door-reminders/${encodeURIComponent(String(reminderId || ""))}/confirm-open`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminIgnoreDoorReminder(reminderId, payload = {}) {
  return apiRequest({
    url: `/admin/door-reminders/${encodeURIComponent(String(reminderId || ""))}/ignore`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminGetLabScheduleDay(labId, dateText = "") {
  const q = toQuery({ date: dateText });
  return apiRequest({
    url: `/admin/labs/${encodeURIComponent(String(labId || ""))}/schedule/day${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminGetLabScheduleWeek(labId, dateText = "") {
  const q = toQuery({ date: dateText });
  return apiRequest({
    url: `/admin/labs/${encodeURIComponent(String(labId || ""))}/schedule/week${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function listBorrowRequests(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/borrow-requests${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function getBorrowRequestDetail(requestId) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}`,
    method: "GET"
  });
}

export async function createBorrowRequest(payload = {}) {
  return apiRequest({
    url: "/borrow-requests",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function cancelBorrowRequest(requestId) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/cancel`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminApproveBorrowRequest(requestId) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/approve`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminRejectBorrowRequest(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/reject`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminNoteBorrowRequest(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/note`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminRemindBorrowRequest(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/remind`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminMarkBorrowReturned(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/mark-returned`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function getStudentProgress() {
  return apiRequest({
    url: "/student/progress",
    method: "GET"
  });
}

export async function teacherListAttendanceSessions(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/teacher/attendance/sessions${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function teacherCreateAttendanceSession(payload = {}) {
  return apiRequest({
    url: "/teacher/attendance/sessions",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherGetAttendanceSessionDetail(sessionId) {
  return apiRequest({
    url: `/teacher/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}`,
    method: "GET"
  });
}

export async function teacherRefreshAttendanceCode(sessionId) {
  return apiRequest({
    url: `/teacher/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/refresh-code`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherStartAttendanceRecheck(sessionId, payload = {}) {
  return apiRequest({
    url: `/teacher/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/start-recheck`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherCloseAttendanceSession(sessionId) {
  return apiRequest({
    url: `/teacher/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/close`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherResolveAttendanceRecord(recordId, payload = {}) {
  return apiRequest({
    url: `/teacher/attendance/records/${encodeURIComponent(String(recordId || ""))}/resolve`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function listMyActiveAttendanceSessions() {
  return apiRequest({
    url: "/attendance/active-sessions",
    method: "GET"
  });
}

export async function getMyAttendanceSessionDetail(sessionId) {
  return apiRequest({
    url: `/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/me`,
    method: "GET"
  });
}

export async function studentAttendanceCheckIn(sessionId, payload = {}) {
  return apiRequest({
    url: `/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/check-in`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function studentAttendanceRecheck(sessionId, payload = {}) {
  return apiRequest({
    url: `/attendance/sessions/${encodeURIComponent(String(sessionId || ""))}/recheck`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherGetTaskRubric(taskId) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/rubric`,
    method: "GET"
  });
}

export async function teacherSaveTaskRubric(taskId, payload = {}) {
  return apiRequest({
    url: `/teacher/tasks/${encodeURIComponent(String(taskId || ""))}/rubric`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function teacherGetReviewWorkspace(fileId) {
  return apiRequest({
    url: `/teacher/student-files/${encodeURIComponent(String(fileId || ""))}/review-workspace`,
    method: "GET"
  });
}

export async function teacherApplyAiReviewSuggestion(fileId) {
  return apiRequest({
    url: `/teacher/student-files/${encodeURIComponent(String(fileId || ""))}/ai-review-apply`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function teacherBatchApplyAiReviewSuggestions(fileIds = []) {
  return apiRequest({
    url: "/teacher/student-files/ai-review-apply-batch",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: { fileIds: Array.isArray(fileIds) ? fileIds : [] }
  });
}

export async function createReservationWaitlist(payload = {}) {
  return apiRequest({
    url: "/reservations/waitlist",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function listReservationWaitlist(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/reservations/waitlist${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function cancelReservationWaitlist(waitlistId) {
  return apiRequest({
    url: `/reservations/waitlist/${encodeURIComponent(String(waitlistId || ""))}/cancel`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminPromoteReservationWaitlist(waitlistId) {
  return apiRequest({
    url: `/admin/reservation-waitlist/${encodeURIComponent(String(waitlistId || ""))}/promote`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminGetReservationPriorityRules() {
  return apiRequest({
    url: "/admin/reservation-priority-rules",
    method: "GET"
  });
}

export async function adminSaveReservationPriorityRules(payload = {}) {
  return apiRequest({
    url: "/admin/reservation-priority-rules",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminPreviewReservationPriority(payload = {}) {
  return apiRequest({
    url: "/admin/reservation-priority-preview",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function createBorrowRenewRequest(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/renew`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function listBorrowRenewRequests(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/borrow-requests/extensions${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminApproveBorrowRenewRequest(extensionId) {
  return apiRequest({
    url: `/borrow-requests/extensions/${encodeURIComponent(String(extensionId || ""))}/approve`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminRejectBorrowRenewRequest(extensionId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/extensions/${encodeURIComponent(String(extensionId || ""))}/reject`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminAiRemindBorrowRequest(requestId) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/ai-remind`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: {}
  });
}

export async function adminScanReturnBorrowRequest(payload = {}) {
  return apiRequest({
    url: "/borrow-requests/scan-return",
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function listBorrowCompensations(params = {}) {
  const q = toQuery(params || {});
  return apiRequest({
    url: `/borrow-compensations${q ? `?${q}` : ""}`,
    method: "GET"
  });
}

export async function adminCreateBorrowCompensation(requestId, payload = {}) {
  return apiRequest({
    url: `/borrow-requests/${encodeURIComponent(String(requestId || ""))}/compensations`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function adminUpdateBorrowCompensationStatus(compensationId, payload = {}) {
  return apiRequest({
    url: `/borrow-compensations/${encodeURIComponent(String(compensationId || ""))}/status`,
    method: "POST",
    header: { "Content-Type": "application/json" },
    data: payload
  });
}

export async function getWorkbenchOverview() {
  return apiRequest({
    url: "/overview",
    method: "GET"
  });
}
