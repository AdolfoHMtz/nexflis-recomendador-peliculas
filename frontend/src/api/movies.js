import client from './client'

export const search = (q) =>
  client.get('/api/buscar', { params: { q } }).then((r) => r.data)

export const getMovieDetail = (id) =>
  client.get(`/api/movie/${id}`).then((r) => r.data)

export const getHeroOptions = (dimension, q) =>
  client.get('/api/hero/options', { params: { dimension, q } }).then((r) => r.data)

export const heroSearch = (selected, logicMode) =>
  client.post('/api/hero/search', { selected, logicMode }).then((r) => r.data)

export const getIRMetrics = () =>
  client.get('/api/recomendacion/ir-metrics').then((r) => r.data)

export const recomendar = (movieId, titulo, minutos, reaccion, diffOpts = {}) =>
  client.post('/api/recomendar', { movie_id: String(movieId), titulo, minutos, reaccion, diff_opts: diffOpts }).then((r) => r.data)

export const getHome = () =>
  client.get('/api/home').then((r) => r.data)

export const getUserHistorial = () =>
  client.get('/api/usuario/historial').then((r) => r.data)

export const getUltimaConsulta = () =>
  client.get('/api/usuario/ultima-consulta').then((r) => r.data)
