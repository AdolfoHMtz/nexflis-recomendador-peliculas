import client from './client'

export const login = (username, password) =>
  client.post('/api/auth/login', { username, password }).then((r) => r.data)

export const register = (username, password, edad, email) =>
  client.post('/api/auth/register', { username, password, edad, email }).then((r) => r.data)

export const logout = () =>
  client.post('/api/auth/logout').then((r) => r.data)

export const getMe = () =>
  client.get('/api/auth/me').then((r) => r.data)

export const updateProfile = (fields) =>
  client.patch('/api/users/me', fields).then((r) => r.data)

export const deleteAccount = (password_actual) =>
  client.delete('/api/users/me', { data: { password_actual } }).then((r) => r.data)
