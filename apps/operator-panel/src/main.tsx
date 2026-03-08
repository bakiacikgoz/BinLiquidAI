import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Import new modular CSS architecture
import './styles/tokens.css'
import './styles/themes/dark.css'
import './styles/themes/light.css'
import './styles/base.css'
import './index.css'  // Keep existing styles for backwards compatibility

import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
