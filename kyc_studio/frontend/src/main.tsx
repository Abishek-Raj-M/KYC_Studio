import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { ThemeProvider } from './context/ThemeContext'
import { KYCProvider } from './context/KYCContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <KYCProvider>
        <App />
      </KYCProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
