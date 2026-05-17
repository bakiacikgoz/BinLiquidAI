import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Import new modular CSS architecture
import './styles/tokens.css'
import './styles/themes/dark.css'
import './styles/themes/light.css'
import './styles/base.css'
import './index.css'  // Keep existing styles for secondary workspaces during migration
import './styles/premium-components.css'
import './styles/premium-shell.css'
import './styles/premium-mission.css'
import './styles/premium-assistant.css'

import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
