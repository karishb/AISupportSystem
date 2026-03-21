import { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, TextField, Select, MenuItem,
  FormControl, InputLabel, Slider, Stack, Chip, Accordion, AccordionSummary,
  AccordionDetails, CircularProgress, Paper
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import axios from 'axios'

const CATEGORIES = ['', 'Billing Inquiry', 'Technical Issue', 'Product Inquiry', 'Refund Request', 'Account Access', 'Shipping Issue', 'Cancellation', 'General Inquiry']
const SENTIMENTS = ['', 'positive', 'neutral', 'negative']

export default function Tickets() {
  const [tickets, setTickets] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [sentiment, setSentiment] = useState('')
  const [minFrustration, setMinFrustration] = useState(0)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(fetchTickets, 300)
    return () => clearTimeout(timer)
  }, [category, sentiment, minFrustration, search])

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const params = { limit: 50 }
      if (category) params.category = category
      if (sentiment) params.sentiment = sentiment
      if (minFrustration > 0) params.min_frustration = minFrustration
      if (search) params.search = search
      const r = await axios.get('/api/tickets', { params })
      setTickets(r.data.tickets || [])
      setTotal(r.data.total || 0)
    } catch { setTickets([]) }
    setLoading(false)
  }

  const sentimentColor = (s) => s === 'positive' ? 'success' : s === 'negative' ? 'error' : 'default'
  const frustColor = (f) => f > 0.7 ? 'error' : f > 0.4 ? 'warning' : 'success'

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>Tickets ({total})</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
            <TextField label="Search" size="small" value={search} onChange={e => setSearch(e.target.value)} sx={{ minWidth: 200 }} />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Category</InputLabel>
              <Select value={category} label="Category" onChange={e => setCategory(e.target.value)}>
                {CATEGORIES.map(c => <MenuItem key={c} value={c}>{c || 'All'}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel>Sentiment</InputLabel>
              <Select value={sentiment} label="Sentiment" onChange={e => setSentiment(e.target.value)}>
                {SENTIMENTS.map(s => <MenuItem key={s} value={s}>{s || 'All'}</MenuItem>)}
              </Select>
            </FormControl>
            <Box sx={{ minWidth: 200 }}>
              <Typography variant="caption">Min Frustration: {minFrustration}</Typography>
              <Slider value={minFrustration} onChange={(_, v) => setMinFrustration(v)} min={0} max={1} step={0.1} size="small" />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}><CircularProgress /></Box>
      ) : tickets.length === 0 ? (
        <Typography color="text.secondary" textAlign="center" py={4}>No tickets found</Typography>
      ) : (
        tickets.map(t => (
          <Accordion key={t.id} sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ width: '100%', mr: 2 }}>
                <Typography variant="body2" sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.message?.slice(0, 100)}...
                </Typography>
                <Chip label={t.ai_category} size="small" color="primary" variant="outlined" />
                <Chip label={t.ai_sentiment} size="small" color={sentimentColor(t.ai_sentiment)} />
                <Chip label={`${(t.ai_frustration || 0).toFixed(2)}`} size="small" color={frustColor(t.ai_frustration)} variant="outlined" />
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="subtitle2" gutterBottom>Customer Message</Typography>
              <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                <Typography variant="body2">{t.message}</Typography>
              </Paper>
              <Typography variant="subtitle2" gutterBottom>AI Suggested Response</Typography>
              <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'primary.50', borderColor: 'primary.200' }}>
                <Typography variant="body2">{t.ai_response || 'No response generated'}</Typography>
              </Paper>
              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                <Typography variant="caption">ID: {t.ticket_id}</Typography>
                <Typography variant="caption">Channel: {t.channel}</Typography>
                <Typography variant="caption">Product: {t.product}</Typography>
                <Typography variant="caption">Order: ${t.order_value?.toFixed(2)}</Typography>
                <Typography variant="caption">Status: {t.resolution_status}</Typography>
                <Typography variant="caption">Confidence: {((t.ai_confidence || 0) * 100).toFixed(0)}%</Typography>
              </Stack>
            </AccordionDetails>
          </Accordion>
        ))
      )}
    </Box>
  )
}
