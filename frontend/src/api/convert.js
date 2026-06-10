import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function convertDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await client.post('/convert', formData)
  return response.data
}

export async function batchConvertDocuments(files) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  const response = await client.post('/batch-convert', formData)
  return response.data
}

export async function generateXml(article) {
  const response = await client.post('/generate-xml', { article })
  return response.data
}

export async function exportPackage(payload) {
  const response = await client.post('/export-package', payload, { responseType: 'blob' })
  return response.data
}
