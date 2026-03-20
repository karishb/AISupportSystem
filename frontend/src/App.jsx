import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Box, Tabs, Tab } from '@mui/material'
import Upload from './pages/Upload'
import Dashboard from './pages/Dashboard'
import Tickets from './pages/Tickets'
import Assistant from './pages/Assistant'
import Analytics from './pages/Analytics'

const theme = createTheme({
  palette: {
    primary: { main: '#1565c0' },
    secondary: { main: '#e91e63' },
    background: { default: '#f5f5f5' },
  },
})

const NAV = [
  { label: 'Upload Data', path: '/' },
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Tickets', path: '/tickets' },
  { label: 'AI Assistant', path: '/assistant' },
  { label: 'Analytics', path: '/analytics' },
]

function NavBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const current = NAV.findIndex(n => n.path === location.pathname)

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <Typography variant="h6" sx={{ mr: 4, fontWeight: 700 }}>
          Support Insight
        </Typography>
        <Tabs
          value={current >= 0 ? current : 0}
          onChange={(_, idx) => navigate(NAV[idx].path)}
          textColor="inherit"
          indicatorColor="secondary"
        >
          {NAV.map(n => <Tab key={n.path} label={n.label} />)}
        </Tabs>
      </Toolbar>
    </AppBar>
  )
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <NavBar />
        <Box sx={{ maxWidth: 1400, mx: 'auto', p: 3 }}>
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/tickets" element={<Tickets />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  )
}
