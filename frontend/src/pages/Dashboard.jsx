import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Grid, Card, CardContent, Typography, Alert, CircularProgress,
  Chip, Button, Stack
} from '@mui/material'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import WarningIcon from '@mui/icons-material/Warning'
import axios from 'axios'

const COLORS = ['#1565c0', '#e91e63', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#795548', '#607d8b']

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/dashboard')
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Box display="flex" justifyContent="center" p={8}><CircularProgress /></Box>

  if (!stats || stats.total_tickets === 0) {
    return (
      <Box textAlign="center" py={8}>
        <Typography variant="h5" gutterBottom>No Data Yet</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Upload customer support tickets to see insights here.
        </Typography>
        <Button variant="contained" onClick={() => navigate('/')}>Upload Data</Button>
      </Box>
    )
  }

  const StatCard = ({ title, value, color = 'primary.main' }) => (
    <Card>
      <CardContent>
        <Typography color="text.secondary" variant="body2" gutterBottom>{title}</Typography>
        <Typography variant="h4" sx={{ color }}>{value}</Typography>
      </CardContent>
    </Card>
  )

  const sentimentData = Object.entries(stats.sentiment_distribution || {}).map(([name, value]) => ({ name, value }))

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>Dashboard</Typography>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Total Tickets" value={stats.total_tickets.toLocaleString()} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Avg Frustration" value={stats.avg_frustration} color="warning.main" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Revenue at Risk" value={`$${stats.revenue_at_risk.toLocaleString()}`} color="error.main" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard title="Projected Savings" value={`$${stats.cost_savings?.cost_savings_usd?.toLocaleString() || 0}`} color="success.main" />
        </Grid>
      </Grid>

      {stats.anomalies?.length > 0 && (
        <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 3 }}>
          <Typography variant="subtitle2">Anomaly Detected</Typography>
          {stats.anomalies.map((a, i) => (
            <Typography key={i} variant="body2">
              <strong>{a.category}</strong>: {a.spike_percentage}% spike above baseline
            </Typography>
          ))}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Top Issues by Category</Typography>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={stats.top_issues}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" angle={-30} textAnchor="end" height={100} fontSize={12} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#1565c0" name="Tickets" />
                  <Bar dataKey="revenue_at_risk" fill="#e91e63" name="Revenue at Risk ($)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Sentiment Distribution</Typography>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie data={sentimentData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                    {sentimentData.map((_, i) => (
                      <Cell key={i} fill={['#4caf50', '#ff9800', '#f44336'][i] || '#999'} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
