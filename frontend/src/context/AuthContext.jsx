import { createContext, useContext, useEffect, useState } from 'react'
import { getMe, login as apiLogin, logout as apiLogout, register as apiRegister } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Al montar, verificar si hay sesión activa en el servidor (cookie Flask)
  useEffect(() => {
    getMe()
      .then((data) => setUser(data.authenticated ? data : null))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const data = await apiLogin(username, password)
    // El servidor establece la cookie de sesión Flask; solo guardamos el estado en React
    setUser({ authenticated: true, ...data.user })
    return data
  }

  const register = async (username, password, edad, email) => {
    const data = await apiRegister(username, password, edad, email)
    setUser({ authenticated: true, ...data.user })
    return data
  }

  const logout = async () => {
    await apiLogout().catch(() => {})
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
