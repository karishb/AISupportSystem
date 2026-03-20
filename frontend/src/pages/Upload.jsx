import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Card, CardContent, Typography, LinearProgress,
  Alert, Chip, Stack, Divider, Paper, Slider
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import DeleteIcon from '@mui/icons-material/Delete'
import StopCircleIcon from '@mui/icons-material/StopCircle'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import axios from 'axios'

export default function Upload() {
  const [status, setStatus] = useState(null) // pipeline status
  const [mode, setMode] = useState(null)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState(null)
  const [sampleSize, setSampleSize] = useState(30)
  const fileRef = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/mode').then(r => setMode(r.data)).catch(() => {})
    // Check if pipeline is already running
    axios.get('/api/pipeline/status').then(r => {
      if (r.data.state === 'running') {
        setStatus(r.data)
        setPolling(true)
      } else if (r.data.state === 'done') {
        setStatus(r.data)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!polling) return
    const interval = setInterval(async () => {
      try {
        const r = await axios.get('/api/pipeline/status')
        setStatus(r.data)
        if (r.data.state !== 'running') {
          setPolling(false)
        }
      } catch { setPolling(false) }
    }, 1000)
    return () => clearInterval(interval)
  }, [polling])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    const form = new FormData()
    form.append('file', file)
    form.append('sample_size', String(sampleSize))
    try {
      await axios.post('/api/upload', form)
      setPolling(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    }
  }

  const handleGenerate = async () => {
    setError(null)
    try {
      await axios.post(`/api/generate-sample?count=5000&sample_size=${sampleSize}`)
      setPolling(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed')
    }
  }

  const handleReset = async () => {
    try {
      await axios.post('/api/reset')
      setStatus(null)
      setError(null)
    } catch (err) {
      setError('Reset failed')
    }
  }

  const progress = status?.total > 0 ? (status.processed / status.total) * 100 : 0

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>
        Customer Support Insight Platform
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Upload customer support tickets to analyze with AI. The pipeline will categorize issues,
        detect sentiment, and generate suggested responses.
      </Typography>

      {mode && (
        <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
          <Chip label={`LLM: ${mode.llm_provider}`} color={mode.mode === 'llm' ? 'success' : 'default'} size="small" />
          <Chip label={`Embeddings: ${mode.embeddings}`} color={mode.embeddings !== 'disabled' ? 'info' : 'default'} size="small" />
          <Chip label={`Vector DB: ${mode.vector_db}`} size="small" />
        </Stack>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Upload Controls */}
      {(!status || status.state === 'idle' || status.state === 'error') && (
        <>
        <Card sx={{ mb: 2, p: 2 }}>
          <CardContent sx={{ pb: '16px !important' }}>
            <Typography variant="subtitle2" gutterBottom>
              Tickets to process with AI: <strong>{sampleSize}</strong>
            </Typography>
            <Slider
              value={sampleSize} onChange={(_, v) => setSampleSize(v)}
              min={10} max={500} step={10}
              marks={[{value: 10, label: '10'}, {value: 50, label: '50'}, {value: 100, label: '100'}, {value: 250, label: '250'}, {value: 500, label: '500'}]}
              valueLabelDisplay="auto"
            />
            <Typography variant="caption" color="text.secondary">
              Lower = faster processing, less API usage. Each ticket uses ~3 Groq API calls.
            </Typography>
          </CardContent>
        </Card>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }}>
          <Card sx={{ flex: 1, textAlign: 'center', p: 2 }}>
            <CardContent>
              <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6" gutterBottom>Upload CSV</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Upload your own customer support ticket CSV file
              </Typography>
              <input type="file" accept=".csv" ref={fileRef} onChange={handleUpload} hidden />
              <Button variant="contained" onClick={() => fileRef.current?.click()}>
                Choose File
              </Button>
            </CardContent>
          </Card>

          <Card sx={{ flex: 1, textAlign: 'center', p: 2 }}>
            <CardContent>
              <AutoFixHighIcon sx={{ fontSize: 48, color: 'secondary.main', mb: 1 }} />
              <Typography variant="h6" gutterBottom>Generate Sample Data</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Generate 5,000 synthetic tickets and process {sampleSize} with AI
              </Typography>
              <Button variant="contained" color="secondary" onClick={handleGenerate}>
                Generate & Process
              </Button>
            </CardContent>
          </Card>
        </Stack>
        </>
      )}

      {/* Processing Progress */}
      {status && status.state === 'running' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="h6">Processing Pipeline</Typography>
              <Button
                variant="outlined" color="error" size="small"
                startIcon={<StopCircleIcon />}
                onClick={async () => {
                  try { await axios.post('/api/pipeline/stop') } catch {}
                }}
              >
                Stop
              </Button>
            </Stack>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 10, borderRadius: 5, mb: 2 }} />
            <Typography variant="body2" color="text.secondary">
              {status.current_step}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {status.processed} / {status.total} tickets processed ({Math.round(progress)}%)
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {status && status.state === 'done' && status.results && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
              <CheckCircleIcon color="success" />
              <Typography variant="h6">Pipeline Complete</Typography>
            </Stack>
            <Typography variant="body1" sx={{ mb: 2 }}>
              {status.message}
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>Category Distribution</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
              {Object.entries(status.results.categories || {}).map(([cat, count]) => (
                <Chip key={cat} label={`${cat}: ${count}`} variant="outlined" size="small" />
              ))}
            </Stack>

            <Typography variant="subtitle2" gutterBottom>Sentiment Distribution</Typography>
            <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
              {Object.entries(status.results.sentiments || {}).map(([sent, count]) => (
                <Chip
                  key={sent}
                  label={`${sent}: ${count}`}
                  color={sent === 'positive' ? 'success' : sent === 'negative' ? 'error' : 'default'}
                  size="small"
                />
              ))}
            </Stack>

            <Typography variant="body2" color="text.secondary">
              Average Frustration: {status.results.avg_frustration}
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={() => navigate('/dashboard')}>
                View Dashboard
              </Button>
              <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={handleReset}>
                Reset & Start Over
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}

      {status && status.state === 'error' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Alert severity="error" sx={{ mb: 2 }}>
              Pipeline error: {status.message?.slice(0, 200)}...
            </Alert>
            <Button variant="contained" color="error" startIcon={<DeleteIcon />} onClick={handleReset} size="large">
              Reset & Start Over
            </Button>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
