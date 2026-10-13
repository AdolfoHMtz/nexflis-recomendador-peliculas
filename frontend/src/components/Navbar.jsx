import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import PersonIcon from '@mui/icons-material/Person'
import LogoutIcon from '@mui/icons-material/Logout'
import { useAuth } from '../context/AuthContext'
import { useReco } from '../context/RecoContext'
import SearchBar from './search/SearchBar'
import WatchModal from './recommendation/WatchModal'
import InfoModal from './recommendation/InfoModal'
import ProfileModal from './auth/ProfileModal'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { triggerRecommendation } = useReco()
  const navigate = useNavigate()
  const [infoMovie, setInfoMovie] = useState(null)
  const [watchMovie, setWatchMovie] = useState(null)
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <>
      <nav style={{
        background: 'rgba(10,10,15,0.97)', borderBottom: '1px solid #1a1a2e',
        backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)',
        padding: '10px 24px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 1000,
      }}>
        <Link to="/" style={{ fontSize: '1.6rem', fontWeight: 700, textDecoration: 'none', color: '#e50914', letterSpacing: '-1px' }}>
          NEXFLIS
        </Link>

        <SearchBar onSelectMovie={(m) => setInfoMovie(m)} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          {user ? (
            <>
              <Chip
                icon={<PersonIcon sx={{ fontSize: '0.9rem !important' }} />}
                label={user.username}
                size="small"
                onClick={() => setProfileOpen(true)}
                sx={{
                  background: '#1a1a2e', color: '#9ca3af', border: '1px solid #2a2a4a',
                  fontSize: '.78rem', cursor: 'pointer',
                  '&:hover': { borderColor: '#e50914', color: '#e5e5e5', background: '#22223a' },
                }}
              />
              <Button
                size="small" variant="outlined" startIcon={<LogoutIcon sx={{ fontSize: '0.85rem !important' }} />}
                onClick={async () => { await logout(); navigate('/login') }}
                sx={{
                  fontSize: '.75rem', borderColor: '#2a2a4a', color: '#9ca3af', textTransform: 'none',
                  borderRadius: 6, '&:hover': { borderColor: '#e50914', color: '#e5e5e5', background: 'transparent' },
                }}
              >
                Salir
              </Button>
            </>
          ) : (
            <>
              <Button component={Link} to="/login" size="small" variant="outlined"
                sx={{
                  fontSize: '.75rem', borderColor: 'rgba(255,255,255,.3)', color: '#e5e5e5', textTransform: 'none',
                  borderRadius: 6, '&:hover': { borderColor: '#fff', background: 'rgba(255,255,255,.05)' },
                }}
              >
                Iniciar sesión
              </Button>
              <Button component={Link} to="/register" size="small" variant="contained"
                sx={{
                  fontSize: '.75rem', background: '#e50914', textTransform: 'none', borderRadius: 6,
                  '&:hover': { background: '#b20710' },
                }}
              >
                Registrarse
              </Button>
            </>
          )}
        </div>
      </nav>

      {infoMovie && (
        <InfoModal movie={infoMovie} onClose={() => setInfoMovie(null)}
          onWatch={(m) => { setInfoMovie(null); setWatchMovie(m) }} />
      )}
      {watchMovie && (
        <WatchModal movie={watchMovie} onClose={() => setWatchMovie(null)}
          onSubmit={async (m, min, rea, diff) => { setWatchMovie(null); triggerRecommendation(m, min, rea, diff) }} />
      )}
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </>
  )
}
