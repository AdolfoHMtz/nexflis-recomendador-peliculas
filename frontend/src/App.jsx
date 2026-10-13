import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { AuthProvider } from './context/AuthContext'
import { useAuth } from './context/AuthContext'
import { RecoProvider } from './context/RecoContext'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import AuthPage from './pages/AuthPage'
import './App.css'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null  // espera a que el auth context cargue
  if (!user) return <Navigate to="/login" replace />
  return children
}

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#0a0a0f', paper: '#12121f' },
    primary: { main: '#e50914' },
  },
  typography: { fontFamily: "'Inter', sans-serif" },
  components: {
    MuiDialog: {
      defaultProps: { disableScrollLock: true },
    },
  },
})

function Layout() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
        <Route path="/login" element={<AuthPage defaultTab="login" />} />
        <Route path="/register" element={<AuthPage defaultTab="register" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <RecoProvider>
            <Layout />
          </RecoProvider>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
