import { createContext, useContext, useRef } from 'react'

const RecoContext = createContext(null)

/**
 * Permite que el Navbar dispare recomendaciones en HomePage.
 * HomePage registra su handleWatch con registerHandler().
 * Navbar lo invoca con triggerRecommendation().
 */
export function RecoProvider({ children }) {
  const handlerRef = useRef(null)

  const registerHandler = (fn) => { handlerRef.current = fn }
  const triggerRecommendation = (movie, minutos, reaccion, diffOpts = {}) => {
    handlerRef.current?.(movie, minutos, reaccion, diffOpts)
  }

  return (
    <RecoContext.Provider value={{ registerHandler, triggerRecommendation }}>
      {children}
    </RecoContext.Provider>
  )
}

export const useReco = () => useContext(RecoContext)
