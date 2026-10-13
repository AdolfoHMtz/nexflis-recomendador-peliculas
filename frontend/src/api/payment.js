import client from './client'

export const getPlan = () =>
  client.get('/api/suscripcion/plan').then(r => r.data)

export const pagar = (numero_tarjeta) =>
  client.post('/api/suscripcion/pagar', { numero_tarjeta }).then(r => r.data)

export const verificarTransaccion = (txn_id) =>
  client.get(`/api/transacciones/${txn_id}/verificar`).then(r => r.data)

export const descargarPDF = async (txn_id) => {
  const res = await client.get(`/api/transacciones/${txn_id}/pdf`, { responseType: 'blob' })
  _triggerDownload(res.data, `comprobante_${txn_id}.pdf`)
}

export const descargarUltimoPDF = async () => {
  const res = await client.get('/api/suscripcion/ultimo-comprobante/pdf', { responseType: 'blob' })
  _triggerDownload(res.data, 'comprobante_nexflis.pdf')
}

export const verificarPayload = (payload_cifrado, hmac_firma) =>
  client.post('/api/transacciones/verificar-payload', { payload_cifrado, hmac_firma }).then(r => r.data)

function _triggerDownload(blob, filename) {
  const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
