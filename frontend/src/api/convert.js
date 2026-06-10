import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function convertDocument(file, profile = 'default') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('profile', profile)
  const response = await client.post('/convert', formData)
  return response.data
}

export async function batchConvertDocuments(files, profile = 'default') {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('profile', profile)
  const response = await client.post('/batch-convert', formData)
  return response.data
}

export async function getProfiles() {
  const response = await client.get('/profiles')
  return response.data.profiles
}

export async function getDemoDocument() {
  const response = await client.get('/demo-document', { responseType: 'blob' })
  return new File([response.data], 'word2jats_feature_acceptance.docx', {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  })
}

export async function generateXml(article) {
  const response = await client.post('/generate-xml', { article })
  return response.data
}

export async function exportPackage(payload) {
  const response = await client.post('/export-package', payload, { responseType: 'blob' })
  return response.data
}
