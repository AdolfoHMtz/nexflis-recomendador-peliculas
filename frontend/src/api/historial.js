import client from './client'

export const descargarHistorialPDF = async (username) => {
  const res = await client.get('/api/usuario/historial/pdf', { responseType: 'blob' })
  _triggerDownload(res.data, `historial_${username || 'nexflis'}.pdf`, 'application/pdf')
}

export const descargarHistorialXML = async (username) => {
  const res = await client.get('/api/usuario/historial/xml', { responseType: 'blob' })
  _triggerDownload(res.data, `historial_${username || 'nexflis'}.xml`, 'application/xml')
}

export const descifrarHistorialXML = (xml) =>
  client.post('/api/usuario/historial/descifrar', { xml }).then(r => r.data)

function _triggerDownload(blob, filename, mimeType) {
  const url = URL.createObjectURL(new Blob([blob], { type: mimeType }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
