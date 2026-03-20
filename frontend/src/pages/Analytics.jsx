import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Grid, Card, CardContent, Typography, CircularProgress, Button
} from '@mui/material'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import axios from 'axios'

const COLORS = ['#1565c0', '#e91e63', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#795548', '#607d8b']

export default function Analytics() {
  const [stats, setStats] = useState(null)
  const [trends, setTrends] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      axios.get('/api/dashboard'),
      axios.get('/api/trends'),
    ]).then(([dashRes, trendRes]) => {
      setStats(dashRes.data)
      setTrends(trendRes.data.daily_trends || [])
    }).catch(() => {})
    .finally(() => setLoading(false))
  }, [])

  if (loading) return <Box display="flex" justifyContent="center" p={8}><CircularProgress /></Box>

  if (!stats || stats.total_tickets === 0) {
    return (
      <Box textAlign="center" py={8}>
        <Typography variant="h5" gutterBottom>No Data Yet</Typography>
        <Button variant="contained" onClick={() => navigate('/')}>Upload Data</Button>
      </Box>
    )
  }

  const catData = Object.entries(stats.category_distribution || {}).map(([name, value]) => ({ name, value }))
  const costData = stats.cost_savings || {}

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>Analytics</Typography>

      <Grid container spacing={3}>
        {/* Daily Trends */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Daily Ticket Volume & Frustration</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={11} />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" domain={[0, 1]} />
                  <Tooltip />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="count" stroke="#1565c0" name="Ticket Count" strokeWidth={2} />
                  <Line yAxisId="right" type="monotone" dataKey="avg_frustration" stroke="#e91e63" name="Avg Frustration" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Category Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Category Distribution</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={catData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`} labelLine={false}>
                    {catData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Revenue at Risk by Category */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Revenue at Risk by Category</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={(stats.top_issues || []).filter(i => i.revenue_at_risk > 0)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" fontSize={11} angle={-20} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
                  <Bar dataKey="revenue_at_risk" fill="#e91e63" name="Revenue at Risk ($)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Cost Savings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Projected Cost Savings (AI Automation)</Typography>
              <Grid container spacing={3}>
                <Grid item xs={4}>
                  <Typography variant="h4" color="primary">{costData.automatable_tickets}</Typography>
                  <Typography variant="body2" color="text.secondary">Automatable Tickets (40%)</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h4" color="primary">{costData.hours_saved}h</Typography>
                  <Typography variant="body2" color="text.secondary">Agent Hours Saved</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h4" color="success.main">${costData.cost_savings_usd?.toLocaleString()}</Typography>
                  <Typography variant="body2" color="text.secondary">Monthly Savings (at $25/hr)</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
