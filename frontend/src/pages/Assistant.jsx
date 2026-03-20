import { useState, useEffect } from 'react'
import {
  Box, Typography, TextField, Button, Card, CardContent, Chip, Stack,
  CircularProgress, Paper, Divider, Alert
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import axios from 'axios'

export default function Assistant() {
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState(null)

  useEffect(() => {
    axios.get('/api/mode').then(r => setMode(r.data)).catch(() => {})
  }, [])

  const analyze = async () => {
    if (!message.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const r = await axios.post('/api/analyze', { message })
      setResult(r.data)
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Analysis failed' })
    }
    setLoading(false)
  }

  const sentimentColor = (s) => s === 'positive' ? 'success' : s === 'negative' ? 'error' : 'warning'

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>AI Assistant</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Paste any customer support message to get instant AI analysis: categorization,
        sentiment detection, and a suggested response.
      </Typography>

      {mode && (
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Chip label={mode.llm_provider} color="success" size="small" />
          <Chip label={mode.responses} size="small" />
        </Stack>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <TextField
            fullWidth multiline rows={4}
            placeholder="Type or paste a customer support message here..."
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={e => e.ctrlKey && e.key === 'Enter' && analyze()}
            sx={{ mb: 2 }}
          />
          <Button
            variant="contained" endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
            onClick={analyze} disabled={loading || !message.trim()}
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </Button>
        </CardContent>
      </Card>

      {result?.error && <Alert severity="error">{result.error}</Alert>}

      {result && !result.error && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Analysis Results</Typography>

            <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">Category</Typography>
                <Box><Chip label={result.category} color="primary" /></Box>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Confidence</Typography>
                <Box><Chip label={`${(result.confidence * 100).toFixed(0)}%`} variant="outlined" /></Box>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Sentiment</Typography>
                <Box><Chip label={result.sentiment} color={sentimentColor(result.sentiment)} /></Box>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Frustration</Typography>
                <Box><Chip label={result.frustration_score.toFixed(2)} color={result.frustration_score > 0.7 ? 'error' : result.frustration_score > 0.4 ? 'warning' : 'success'} variant="outlined" /></Box>
              </Box>
            </Stack>

            <Typography variant="subtitle2" gutterBottom>Reasoning</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{result.reasoning}</Typography>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>Suggested Response</Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'success.50', borderColor: 'success.200' }}>
              <Typography variant="body2">{result.suggested_response}</Typography>
            </Paper>

            {result.similar_tickets?.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" gutterBottom>Similar Resolved Tickets (RAG)</Typography>
                {result.similar_tickets.map((s, i) => (
                  <Paper key={i} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip label={s.category} size="small" variant="outlined" />
                      <Chip label={`${(s.similarity * 100).toFixed(0)}% similar`} size="small" />
                    </Stack>
                    <Typography variant="body2" sx={{ mt: 0.5 }}>{s.message}</Typography>
                    {s.resolution && (
                      <Typography variant="body2" color="success.main" sx={{ mt: 0.5 }}>
                        Resolution: {s.resolution}
                      </Typography>
                    )}
                  </Paper>
                ))}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
