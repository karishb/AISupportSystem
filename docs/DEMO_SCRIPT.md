# Demo Video Script (5-10 minutes)

## [0:00-0:30] Intro

- Open browser at your deployed URL (or http://localhost:3000)
- You land on the **Upload Data** page

> "This is my AI-Powered Customer Support Insight Platform. It ingests support tickets, runs them through an AI pipeline, and produces business insights. Let me walk you through it."

---

## [0:30-2:00] Upload and Pipeline Demo

1. **Point at the chips** at the top: LLM, Embeddings, Vector DB
   > "The system uses Groq's free Llama 3.3 70B for LLM analysis, sentence-transformers for embeddings, and ChromaDB for vector search. All completely free."

2. **Drag the slider** to 30
   > "I can control how many tickets to process with AI. Each ticket uses one LLM call for categorization and sentiment, plus one for response generation."

3. **Click "Choose File"** -> navigate to `data/` -> select `customer_support_tickets.csv`
   > "I'm uploading a real Kaggle dataset of 8,400+ customer support tickets. The pipeline will sample 30 and process them with AI."

4. **Watch the progress bar** fill up
   - Point at progress text: "Processing ticket 5/30 - Category: Technical Issue (90%)"
   > "You can see each ticket being categorized in real-time. The pipeline cleans the data, replaces placeholders with actual product names, then runs AI analysis."
   - Point at the Stop button
   > "There's a stop button if I want to cancel mid-run."

5. **When complete**, point at the results:
   - Category chips: Technical Issue, Account Access, Refund Request
   - Sentiment chips: negative, neutral, positive
   > "30 tickets processed. We can see the category and sentiment distribution right here."

6. **Click "View Dashboard"**

---

## [2:00-3:30] Dashboard

1. **Point at the 4 KPI cards**:
   - Total Tickets -> "30 tickets in the system"
   - Avg Frustration -> "0.67 out of 1.0 - customers are fairly frustrated"
   - Revenue at Risk -> "$2,181 in order value from high-frustration customers"
   - Projected Savings -> "AI automation could save $40 on this batch alone"

2. **Point at the yellow Anomaly alert**:
   > "The system detected an anomaly - Technical Issues spiked above the baseline. This is the bonus anomaly detection feature."

3. **Point at "Top Issues by Category" bar chart**:
   > "Bar chart shows Technical Issue is the top category. The pink bars show revenue at risk per category - this tells leadership where to invest."

4. **Point at "Sentiment Distribution" pie chart**:
   > "80% negative sentiment - expected for support tickets. But if this changes over time, it signals a systemic issue."

5. **Scroll down** to cost savings section
   > "Projected cost savings from AI-automating 40% of responses."

---

## [3:30-5:00] Tickets Page

1. **Click "TICKETS"** in the nav bar

2. **Point at the filters row**:
   > "Every ticket is searchable and filterable."

3. **Click Category dropdown** -> select "Account Access"
   > "Filtering to just Account Access tickets."

4. **Clear the filter**

5. **Drag "Min Frustration" slider** to 0.8
   > "Now showing only high-frustration tickets - these need immediate attention."

6. **Reset slider to 0**

7. **Click the expand arrow** on the first ticket
   - Point at "Customer Message"
   > "Here's the full customer message - notice the product name is resolved, not a placeholder."
   - Point at "AI Suggested Response"
   > "The AI generated a professional, empathetic response. An agent can use this directly or edit it."
   - Point at metadata row: ID, Channel, Product, Order value, Status, Confidence

8. **Collapse**, expand another one briefly

---

## [5:00-6:00] AI Assistant

1. **Click "AI ASSISTANT"** in the nav bar

2. **Type**: `My laptop screen is flickering and I can't work. I've already tried restarting three times. This is unacceptable for a $1200 laptop.`

3. **Click "Analyze"**

4. **Point at results**:
   - Category: Technical Issue -> "Correctly categorized"
   - Sentiment: negative -> "Correct - customer is upset"
   - Frustration: 0.9 -> "High frustration detected from the word 'unacceptable'"
   - Suggested Response -> "Professional response with concrete next steps"

5. > "This is what a support agent would see in real-time. Type a customer message, get instant AI analysis and a suggested response. This also uses RAG - as more tickets are processed, ChromaDB finds similar resolved tickets to improve responses."

---

## [6:00-7:00] Analytics

1. **Click "ANALYTICS"** in the nav bar

2. **Point at "Daily Ticket Volume and Frustration" line chart**:
   > "Top chart shows ticket volume over time in blue, and average frustration in pink. Leadership can spot trends."

3. **Point at "Category Distribution" pie chart**:
   > "Category breakdown - Technical Issue dominates."

4. **Point at "Revenue at Risk by Category" bar chart**:
   > "This connects technical problems to business impact."

---

## [7:00-8:00] API and Bonus Features

1. **Open new tab** -> go to `your-url/docs`
   > "FastAPI auto-generates interactive API docs."

2. **Scroll through endpoints** briefly

3. **Click `/api/health`** -> Try it out -> Execute
   - Show response: database up, LLM up, vector DB up
   > "Health monitoring endpoint - shows all system components and their status."

4. **Click `/api/report`** -> Try it out -> Execute
   - Show response: top issues, recommendations, channel breakdown
   > "Automated weekly report - top issues, sentiment distribution, revenue at risk, and actionable recommendations. This could be emailed to leadership weekly."

5. **Click `/api/translate-and-analyze`** -> Try it out
   - Body: `{"message": "Mi computadora no enciende y necesito trabajar urgentemente"}`
   - Execute
   - Show response: detected Spanish, translated, categorized, response in Spanish
   > "Multilingual support - detects Spanish, translates, analyzes, and responds in the original language."

---

## [8:00-9:00] Code and Architecture

1. **Open** `github.com/karishb/AISupportSystem`

2. **Point at file structure**:
   - `ai/` -> "AI module - LLM with multi-key rotation, embeddings, classical ML fallback"
   - `pipeline/` -> "4-stage pipeline: ingest, clean, enrich, store"
   - `backend/` -> "FastAPI with 12+ endpoints"
   - `frontend/` -> "React + Material-UI dashboard"

3. **Click `docs/DESIGN_DOC.md`**:
   > "Design document covers AI choices, data model, scalability path, and tradeoffs"

4. **Click `docs/BUSINESS_INSIGHTS.md`**:
   > "Business document with 3 leadership insights, cost reduction strategy, and metrics to track"

5. **Click `Dockerfile`**:
   > "Multi-stage Docker build - Node builds the frontend, Python serves everything. Deployed on Render with CI/CD via GitHub Actions."

---

## [9:00-9:30] Wrap Up

> "To summarize - this platform uses Groq Llama 3.3 70B for categorization and response generation, sentence-transformers for embeddings, ChromaDB for RAG-based similar ticket search, with TextBlob and TF-IDF as a classical ML fallback. It handles 8,400+ tickets from a real Kaggle dataset, supports multilingual input, detects anomaly spikes, and generates automated reports. All deployed on Render with Docker and CI/CD. Thank you."

---

## Recording Tips

- Use OBS Studio or Windows Game Bar (Win+G) to record
- Keep browser full screen at 1920x1080
- Zoom in (Ctrl++) to 125% so text is readable
- Process the 30 tickets BEFORE recording so results are already there
- Pause between sections - you can edit later
