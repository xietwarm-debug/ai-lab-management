import request from '@/utils/request'

export function getKnowledgeDocuments(params = {}) {
  return request.get('/admin/knowledge/documents', { params })
}

export function getKnowledgeDocumentDetail(id) {
  return request.get(`/admin/knowledge/documents/${id}`)
}

export function createKnowledgeDocument(payload = {}) {
  return request.post('/admin/knowledge/documents', payload)
}

export function uploadKnowledgeDocument(formData) {
  return request.post('/admin/knowledge/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 60000
  })
}

export function updateKnowledgeDocument(id, payload = {}) {
  return request.post(`/admin/knowledge/documents/${id}`, payload)
}

export function updateKnowledgeDocumentStatus(id, payload = {}) {
  return request.post(`/admin/knowledge/documents/${id}/status`, payload)
}

export function reindexKnowledgeDocument(id) {
  return request.post(`/admin/knowledge/documents/${id}/reindex`, {})
}

export function askKnowledgeQuestion(payload = {}) {
  return request.post('/knowledge/ask', payload)
}

export function submitKnowledgeFeedback(payload = {}) {
  return request.post('/knowledge/feedback', payload)
}

export function getKnowledgeFeedbackList(params = {}) {
  return request.get('/admin/knowledge/feedback', { params })
}

export function getUnmatchedKnowledgeQuestions(params = {}) {
  return request.get('/admin/knowledge/unmatched-questions', { params })
}

export function getUnmatchedKnowledgeQuestionDetail(groupKey) {
  return request.get(`/admin/knowledge/unmatched-questions/${groupKey}`)
}

export function updateUnmatchedKnowledgeQuestionStatus(payload = {}) {
  return request.post('/admin/knowledge/unmatched-questions/status', payload)
}
