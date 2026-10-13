import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import BlockIcon from '@mui/icons-material/Block'

export default function AgeBlockModal({ open, onClose, clasificacion, titulo }) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f',
          border: '1px solid #4a1a1a',
          borderRadius: '16px',
          color: '#e5e5e5',
        },
      }}
    >
      <DialogContent sx={{ p: '28px', textAlign: 'center' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af' }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>
        <BlockIcon sx={{ fontSize: '3rem', color: '#dc2626', mb: 1.5 }} />
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 10 }}>
          Contenido restringido
        </div>
        <div style={{ fontSize: '.88rem', color: '#9ca3af', lineHeight: 1.6, marginBottom: 20 }}>
          <strong style={{ color: '#e5e5e5' }}>{titulo}</strong> está clasificada para mayores
          de <strong style={{ color: '#fca5a5' }}>{clasificacion} años</strong>.
          <br />
          No puedes ver esta película con tu edad registrada.
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent', border: '1px solid #4a4a6a', color: '#9ca3af',
            padding: '9px 28px', borderRadius: 30, fontSize: '.85rem', cursor: 'pointer',
          }}
        >
          Entendido
        </button>
      </DialogContent>
    </Dialog>
  )
}
