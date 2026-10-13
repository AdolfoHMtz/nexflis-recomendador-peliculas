import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import LoginForm from '../components/auth/LoginForm'
import RegisterForm from '../components/auth/RegisterForm'

export default function AuthPage({ defaultTab = 'login' }) {
  const [tab, setTab] = useState(defaultTab)
  const navigate = useNavigate()

  const handleSuccess = () => navigate('/')

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">NEXFLIS</div>
        {tab === 'login'
          ? <LoginForm onSuccess={handleSuccess} onGoRegister={() => setTab('register')} />
          : <RegisterForm onSuccess={handleSuccess} onGoLogin={() => setTab('login')} />}
      </div>
    </div>
  )
}
