import axios from 'axios'

// withCredentials: true asegura que la cookie de sesión Flask se envíe en cada request.
// No se usa localStorage ni Bearer token — la autenticación es via cookie HttpOnly del servidor.
const client = axios.create({ baseURL: '/', withCredentials: true })

export default client
