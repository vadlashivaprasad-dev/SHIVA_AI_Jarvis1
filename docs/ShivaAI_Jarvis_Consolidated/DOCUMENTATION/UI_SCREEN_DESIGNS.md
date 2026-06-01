# ShivaAI Jarvis — Complete UI Screen Designs & Wireframes

**Purpose:** Detailed visual design of all major screens  
**Format:** ASCII wireframes + detailed specifications  
**Responsive:** Mobile, Tablet, Desktop  

---

## 1. AUTHENTICATION SCREENS

### 1.1 Login Screen

```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║                  🧠 ShivaAI Jarvis                ║
║            Cognitive Operating System             ║
║                                                   ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ Welcome Back                                │ ║
║  │ Sign in to your account                    │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  Email                                            ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ [email@example.com                        ]│ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  Password                                         ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ [••••••••••••••••••              👁]       │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  ☐ Remember me         Forgot password?           ║
║                                                   ║
║  ┌─────────────────────────────────────────────┐ ║
║  │         Sign In (loading...)               │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  ─────────── or continue with ───────────        ║
║  [Google] [Microsoft] [GitHub]                    ║
║                                                   ║
║  Don't have an account? [Sign up]                 ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Colors:
- Background: White (#FFFFFF)
- Primary input: Neural Purple (#7C51DC)
- Text: Dark Gray (#1A1816)
- Helper text: Medium Gray (#67625D)

Components:
- Logo + brand text (centered top)
- Heading + subheading
- Email input with label
- Password input with show/hide toggle
- Checkbox for "Remember me"
- "Forgot password?" link
- Primary button (Sign In) - purple
- Divider with "or continue with"
- Social auth buttons
- Sign up link at bottom
```

### 1.2 Signup Screen

```
╔═══════════════════════════════════════════════════╗
║                                                   ║
║                  🧠 ShivaAI Jarvis                ║
║                                                   ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ Create Account                              │ ║
║  │ Join ShivaAI today                         │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  Full Name                                        ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ [John Doe                                  ]│ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  Email                                            ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ [user@example.com                          ]│ ║
║  └─────────────────────────────────────────────┘ ║
║  ✓ Available                                      ║
║                                                   ║
║  Password                                         ║
║  ┌─────────────────────────────────────────────┐ ║
║  │ [••••••••••••••••••              👁]       │ ║
║  └─────────────────────────────────────────────┘ ║
║  ⚠ Weak - Add numbers and symbols               ║
║                                                   ║
║  ☐ I agree to the Terms of Service              ║
║  ☐ Subscribe to updates (optional)               ║
║                                                   ║
║  ┌─────────────────────────────────────────────┐ ║
║  │         Create Account                     │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  Already have an account? [Sign in]              ║
║                                                   ║
╚═══════════════════════════════════════════════════╝

Interactive Elements:
- Real-time email validation
- Password strength indicator (weak → strong)
- Terms of service checkbox (required)
- Error messages in red below fields
- Success states (green checkmarks)
```

---

## 2. MAIN APPLICATION SCREENS

### 2.1 Dashboard/Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│ ☰ ShivaAI Jarvis      [🔍 Search] [⚙️ Settings] [👤 Profile]│  ← Header
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  ☰ Sidebar   │             Dashboard / Home                  │
│              │                                                │
│ [+ New Chat] │  ┌──────────────────────────────────────────┐ │
│              │  │  Quick Stats                             │ │
│ Conversations│  │  ┌────────┐ ┌────────┐ ┌────────┐       │ │
│              │  │  │Messages│ │Tokens  │ │Models  │       │ │
│ • Market AI  │  │  │ 247    │ │ 15.2M  │ │ 8      │       │ │
│ • Code Help  │  │  └────────┘ └────────┘ └────────┘       │ │
│ • Teaching   │  └──────────────────────────────────────────┘ │
│              │                                                │
│ Knowledge    │  ┌──────────────────────────────────────────┐ │
│              │  │  Recent Conversations                    │ │
│ • Uploaded   │  │                                          │ │
│ • Indexed    │  │  1. 📈 Market Analysis          2h ago  │ │
│              │  │     "Analyze AAPL stock..."             │ │
│              │  │                                          │ │
│ Trading      │  │  2. 💻 Code Review                1d ago │ │
│              │  │     "Review my Python code..."          │ │
│ • Portfolio  │  │                                          │ │
│ • Strategies │  │  3. 📚 Learning Path              3d ago │ │
│              │  │     "Python Fundamentals"               │ │
│ Code         │  │                                          │ │
│              │  │  [View All]                            │ │
│ • Snippets   │  └──────────────────────────────────────────┘ │
│ • Reviews    │                                                │
│              │  ┌──────────────────────────────────────────┐ │
│ Analytics    │  │  Featured Domains                       │ │
│              │  │                                          │ │
│ • Predictions│  │  [Chat]  [Trading]  [Code]  [Teaching]  │ │
│ • Trends     │  │  [Workflow]  [Voice]  [More]            │ │
│              │  │                                          │ │
│ [Settings]   │  └──────────────────────────────────────────┘ │
│ [Help]       │                                                │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘

Design Details:
- Left sidebar: Dark background, white icons
- Header: Light background, search bar center, profile right
- Main area: 2-3 column grid layout
- Cards: Subtle shadows, rounded corners
- Stats: Large numbers with labels
- Lists: Icons + text with timestamps
- Buttons: Ghost style buttons for "View All"
```

### 2.2 Chat Screen (Main Interface)

```
┌─────────────────────────────────────────────────────────────┐
│ ☰  Chat - Market Analysis    [📋] [⭐] [⋯]                │  ← Header
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  [+ New Chat]│                                                │
│              │                                                │
│  Conversations
│              │  ┌──────────────────────────────────────────┐ │
│  • Market    │  │ You                          10:45 AM   │ │
│    Analysis  │  │ "Analyze the market for tech stocks"    │ │
│              │  └──────────────────────────────────────────┘ │
│  • Code Help │                                                │
│              │  ┌──────────────────────────────────────────┐ │
│  • Teaching  │  │ ShivaAI Jarvis                10:47 AM   │ │
│              │  │                                          │ │
│  • Strategy  │  │ Based on current market conditions:     │ │
│              │  │                                          │ │
│              │  │ • NVDA: Strong uptrend (↑12.5%)        │ │
│              │  │   - Breaking resistance at $800        │ │
│              │  │   - Volume surge indicates strength    │ │
│              │  │                                          │ │
│              │  │ • AAPL: Consolidation phase (→3.2%)     │ │
│              │  │   - Key support at $170                │ │
│              │  │   - Watch for earnings impact          │ │
│              │  │                                          │ │
│              │  │ • META: Recovery signal (↑8.7%)        │ │
│              │  │   - Positive momentum forming          │ │
│              │  │   - Retest of $350 potential          │ │
│              │  │                                          │ │
│              │  │ [Regenerate] [Copy] [Charts] [More...]  │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│  Sidebar     │  ┌──────────────────────────────────────────┐ │
│  Topics      │  │ Input Area                               │ │
│  ═════════   │  ├──────────────────────────────────────────┤ │
│              │  │ Type message... (Shift+Enter for new)    │ │
│              │  │ ▶ Your message appears here...          │ │
│              │  │                                          │ │
│              │  │ [🔗 Attach] [🎤 Voice] [➤ Send]         │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘

Message Styling:
- User message: Right-aligned, neural purple background
- Assistant message: Left-aligned, light gray background
- Code blocks: Syntax highlighted, copy button
- Links: Blue, underlined on hover
- Lists: Bullet points with proper indentation
- Streaming: Character-by-character animation

Interactive Elements:
- Regenerate: Resend same prompt
- Copy: Copy to clipboard (toast feedback)
- Charts: Open visualization modal
- Voice button: Activate microphone
- Stop button: (appears during generation)
```

### 2.3 Trading Dashboard Screen

```
┌─────────────────────────────────────────────────────────────┐
│ ☰  Trading Dashboard                    [📊] [⚙️] [⋯]      │
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  Trading     │  Portfolio Overview                            │
│  ═════════   │  ┌──────────────────────────────────────────┐ │
│              │  │ Balance: $100,000          ↑ +$5,230      │ │
│  • Portfolio │  │ Return: +5.23%             ↑ +0.75%      │ │
│    └ Main    │  │ Risk Score: 6/10 (Medium)                │ │
│    └ Alt     │  │                                          │ │
│              │  │ Equity Curve (30 days)                  │ │
│  • Strategies│  │ ┌──────────────────────────────────────┐ │
│    └ Growth  │  │ │                                    ↗  │ │
│    └ Value   │  │ │                              ↗        │ │
│    └ Momentum│  │ │                    ↗                  │ │
│              │  │ │            ↗                          │ │
│              │  │ │  ↗                                    │ │
│              │  │ └──────────────────────────────────────┘ │
│              │  │ $94K          $100K          $105K       │ │
│  Watchlist   │  └──────────────────────────────────────────┘ │
│              │                                                │
│ • NVDA ↑↑    │  Positions (3 open)                            │
│ • AAPL →     │  ┌─────────────────────────────────────────┐  │
│ • TSLA ↓     │  │ Symbol │ Qty  │ Entry  │ Current │ P&L  │  │
│ • META ↑     │  ├─────────────────────────────────────────┤  │
│              │  │ NVDA   │ 75   │ $750   │ $800    │ +$3750│  │
│              │  │ AAPL   │ 100  │ $150   │ $155    │ +$500 │  │
│              │  │ TSLA   │ 50   │ $260   │ $245    │ -$750 │  │
│              │  │                                          │  │
│              │  │ [Sell] [View Details]                    │  │
│              │  └─────────────────────────────────────────┘  │
│              │                                                │
│              │  Recent Trades                                 │
│              │  ┌─────────────────────────────────────────┐  │
│              │  │ ✓ BUY  NVDA  75 @ $750    Executed     │  │
│              │  │ ✓ BUY  AAPL  100 @ $150   Executed     │  │
│              │  │ ⏳ BUY  META  50 @ $350    Pending       │  │
│              │  │ ✗ SELL TSLA  25 @ $250    Rejected      │  │
│              │  └─────────────────────────────────────────┘  │
│              │                                                │
│              │  [+ New Trade] [Run Strategy] [AI Insight]    │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘

Visual Elements:
- Balance card: Large numbers, color-coded P&L (green/red)
- Chart: Line graph with trend
- Table: Sortable columns, color-coded status
- Watchlist: Simple list with trend indicators (↑↓→)
- Trade status: Icons (✓ done, ⏳ pending, ✗ rejected)
```

### 2.4 Code Assistant Screen

```
┌─────────────────────────────────────────────────────────────┐
│ ☰  Code Assistant               [Python ▼] [📋] [⋯]        │
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  Code        │  Editor                                        │
│  ═════════   │  ┌──────────────────────────────────────────┐ │
│              │  │ 1  def analyze_sentiment(text):           │ │
│  • Snippets  │  │ 2      """Analyze text sentiment"""      │ │
│              │  │ 3      model = SentimentModel()          │ │
│  • Reviews   │  │ 4      return model.predict(text)       │ │
│              │  │ 5                                        │ │
│  • History   │  │ 6  if __name__ == "__main__":           │ │
│              │  │ 7      text = "Great product!"          │ │
│  Recent      │  │ 8      result = analyze_sentiment(text) │ │
│              │  │ 9      print(f"Sentiment: {result}")    │ │
│              │  │                                          │ │
│              │  │                [Copy] [Execute] [Review] │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│              │  Analysis Results                              │
│              │  ┌──────────────────────────────────────────┐ │
│              │  │ ✓ Code Quality: Excellent                │ │
│              │  │   - Clear function names                │ │
│              │  │   - Good docstring                      │ │
│              │  │                                          │ │
│              │  │ ⚡ Performance: Optimizable               │ │
│              │  │   - Cache model loading                 │ │
│              │  │   - Batch process if multiple inputs    │ │
│              │  │                                          │ │
│              │  │ 🔒 Security: Passing                     │ │
│              │  │   - No injection vulnerabilities         │ │
│              │  │   - Proper input validation             │ │
│              │  │                                          │ │
│              │  │ 📈 Complexity: O(n) - Good              │ │
│              │  │                                          │ │
│              │  │ [Generate Tests] [Optimize] [Explain]   │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│              │  Execution Output                              │
│              │  ┌──────────────────────────────────────────┐ │
│              │  │ $ python script.py                       │ │
│              │  │ Sentiment: 0.92 (Very Positive)         │ │
│              │  │ Execution time: 125ms                   │ │
│              │  │                                          │ │
│              │  │ [Run Again] [Clear Output]              │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘

Code Editor Features:
- Syntax highlighting (color-coded keywords)
- Line numbers on left
- Selected language badge (Python, JavaScript, etc.)
- Copy button (top right of code block)

Analysis Section:
- Quality indicators (✓, ⚡, 🔒, 📈)
- Color-coded severity (green/yellow/red)
- Actionable suggestions
- Related action buttons

Execution:
- Terminal-style output area
- Command indicator ($)
- Colored output (errors in red)
```

### 2.5 Learning Path Screen

```
┌─────────────────────────────────────────────────────────────┐
│ ☰  Learning - Python Fundamentals        [📊] [⚙️] [⋯]    │
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│  Learning    │  Progress: ████████░░ 65% Complete            │
│  ═════════   │                                                │
│              │  ┌──────────────────────────────────────────┐ │
│  Paths       │  │ Mastered  Intermediate  Learning  Up Next│ │
│              │  │    ✓           ✓           ○      ○    │ │
│  • Python    │  │ (15)          (8)          (5)    (2)   │ │
│  • JavaScript│  │                                          │ │
│  • Data Sci  │  │ Estimated Completion: 2 weeks (1h/day) │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│  Current     │  Current Lesson: Functions                    │
│  Lesson      │  ┌──────────────────────────────────────────┐ │
│              │  │ What are Functions?                      │ │
│  Functions   │  │                                          │ │
│              │  │ A function is a reusable block of code  │ │
│  Next        │  │ that performs a specific task.          │ │
│              │  │                                          │ │
│  • Classes   │  │ Key concepts:                            │ │
│  • Inheritance│ │ • Input parameters                      │ │
│  • Polymorp. │  │ • Return values                         │ │
│              │  │ • Function scope                        │ │
│              │  │                                          │ │
│              │  │ Example:                                 │ │
│              │  │ def greet(name):                        │ │
│              │  │     return f"Hello, {name}!"           │ │
│              │  │                                          │ │
│              │  │ [Read More] [Examples] [Notes]          │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│  Assessments │  Practice Quiz                                 │
│              │  ┌──────────────────────────────────────────┐ │
│  • Quiz 3/5  │  │ Q: What is the output of this code?    │ │
│  • Project 1 │  │                                          │ │
│              │  │ def add(a, b):                          │ │
│              │  │     return a + b                        │ │
│              │  │                                          │ │
│              │  │ result = add(2, 3)                      │ │
│              │  │                                          │ │
│              │  │ ◯ 5                                      │ │
│              │  │ ◯ "2" + "3"                            │ │
│              │  │ ◯ Error                                 │ │
│              │  │                                          │ │
│              │  │ [Submit Answer]                         │ │
│              │  └──────────────────────────────────────────┘ │
│              │                                                │
│              │  [Previous Lesson] [Next Lesson] [Reset Path] │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘

Visual Elements:
- Progress bar: Horizontal, percentage labeled
- Progress indicators: Checkmarks for completed, circles for pending
- Lesson content: Clean typography, proper spacing
- Quiz: Radio buttons for multiple choice
- Navigation: Previous/Next buttons at bottom
```

### 2.6 Voice Interface Screen

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                         🎤                                  │
│                                                             │
│                    Listening...                             │
│                                                             │
│                 ▌▌▌▌▌▌▌▌▌▌                                  │
│              Voice Level (Medium)                           │
│                                                             │
│                                                             │
│              "Analyze AAPL stock"                           │
│           (Detected text appearing)                         │
│                                                             │
│                                                             │
│                  [⏹ Stop Recording]                         │
│                  [Clear] [Use Text]                         │
│                                                             │
│                                                             │
│              Processing audio...                            │
│              ▓▓▓▓▓▓░░░░░░░░░░░░                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Voice Features:
- Large microphone icon (centered)
- Real-time waveform visualization
- Detected text display (scrolls as it appears)
- Voice level indicator (visual feedback)
- Stop button (prominent red)
- Processing progress (indeterminate)
```

---

## 3. MODAL & DIALOG SCREENS

### 3.1 Settings Modal

```
┌─────────────────────────────────────────────────────┐
│ Settings                                        [✕] │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Appearance                                          │
│ ├─ Theme: [Light ▼] [Dark] [Auto]                │
│ ├─ Font Size: [Normal ▼]                         │
│ └─ Reduced Motion: [ON/OFF]                      │
│                                                     │
│ AI Configuration                                    │
│ ├─ Default Model: [GPT-4 ▼]                      │
│ ├─ Temperature: [0.7 —●—— 1.0]                  │
│ ├─ Max Tokens: [2000]                            │
│ └─ System Prompt: [Edit...]                      │
│                                                     │
│ Voice Settings                                      │
│ ├─ Voice Provider: [OpenAI ▼]                    │
│ ├─ Voice Speed: [1.0x —●— 1.5x]                │
│ └─ Preferred Voice: [Alloy ▼]                   │
│                                                     │
│ Privacy & Data                                      │
│ ├─ ☐ Save conversation history                   │
│ ├─ ☐ Send analytics                              │
│ └─ [Delete All Data]                             │
│                                                     │
│ Integrations                                        │
│ ├─ [Connect Slack]                               │
│ ├─ [Connect Gmail]                               │
│ └─ [Manage API Keys]                             │
│                                                     │
├─────────────────────────────────────────────────────┤
│             [Cancel]                  [Save]        │
└─────────────────────────────────────────────────────┘
```

### 3.2 New Trade Modal

```
┌─────────────────────────────────────────────────────┐
│ New Trade                                       [✕] │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Symbol                                              │
│ ┌──────────────────────────────────────────────┐   │
│ │ [AAPL ▼                                    ]│   │
│ └──────────────────────────────────────────────┘   │
│ Price: $155.20 ↑ +0.50%                            │
│                                                     │
│ Side                                                │
│ ◉ Buy    ◯ Sell                                    │
│                                                     │
│ Quantity                                            │
│ ┌──────────────────────────────────────────────┐   │
│ │ [100                                        ]│   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ Price                                               │
│ ┌──────────────────────────────────────────────┐   │
│ │ [155.20 (market)                            ]│   │
│ └──────────────────────────────────────────────┘   │
│                                                     │
│ Order Summary                                       │
│ ├─ Total Value: $15,520                           │
│ ├─ Commission: $10                                │
│ └─ Risk Score: 6/10 (Medium) ⚠️                  │
│                                                     │
│ ☐ Require approval before execution                │
│                                                     │
├─────────────────────────────────────────────────────┤
│           [Cancel]              [Place Trade]       │
└─────────────────────────────────────────────────────┘
```

---

## 4. MOBILE RESPONSIVE LAYOUTS

### 4.1 Mobile Chat (< 640px)

```
╔════════════════════════════════════╗
║ ≡ Chat - Market AI         ⋯ ⭐   ║  ← Header (compact)
╠════════════════════════════════════╣
║                                    ║
║  You                           📌  ║
║  "Analyze market"                  ║
║                                    ║
║  ShivaAI                           ║
║  Based on current conditions:     ║
║  • NVDA ↑12.5%                     ║
║  • AAPL →3.2%                      ║
║                                    ║
║  [More]                            ║
║                                    ║
║  [Regenerate] [Copy]               ║
║                                    ║
║                                    ║
║  ┌────────────────────────────┐   ║
║  │ Type message...            │   ║
║  │ [🔗] [🎤] [➤]             │   ║
║  └────────────────────────────┘   ║
║                                    ║
╚════════════════════════════════════╝

Mobile Features:
- Hamburger menu (top left) for sidebar
- Compact header with minimal buttons
- Full-width messages
- Bottom sheet for input
- Larger touch targets (44px minimum)
```

### 4.2 Mobile Sidebar Navigation

```
╔════════════════════════════════════╗
║ ShivaAI Jarvis              [✕]   ║
╠════════════════════════════════════╣
║                                    ║
║  [+ New Chat]                      ║
║                                    ║
║  Conversations                     ║
║  • Market Analysis                 ║
║  • Code Review                     ║
║  • Teaching                        ║
║                                    ║
║  Knowledge                         ║
║  • Uploads (3)                     ║
║  • Collections                     ║
║                                    ║
║  Trading                           ║
║  • Portfolios (2)                  ║
║  • Strategies (5)                  ║
║                                    ║
║  Code                              ║
║  • Snippets (12)                   ║
║  • Reviews                         ║
║                                    ║
║  ─────────────────────────         ║
║                                    ║
║  [Settings]                        ║
║  [Help & Feedback]                 ║
║  [Sign Out]                        ║
║                                    ║
╚════════════════════════════════════╝

Mobile Sidebar:
- Full height overlay
- Close button (X) top right
- Swipe gesture to close
- Dark semi-transparent background
```

---

## 5. EMPTY STATES

### 5.1 No Conversations

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                      💬                             │
│                                                     │
│              No Conversations Yet                   │
│                                                     │
│         Start a new chat to begin exploring        │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ [+ Start New Conversation]                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Or try these quick actions:                       │
│  [📈 Market Analysis] [💻 Code Help]              │
│  [📚 Learning Path] [🎯 Trading]                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 Loading State

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                      ⟳                              │
│                 (spinning)                          │
│                                                     │
│              Thinking deeply...                     │
│           Analyzing your request...                │
│                                                     │
│           ⏱ Average response time: 2s              │
│                                                     │
│                  [Cancel]                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.3 Error State

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                      ⚠️                             │
│                                                     │
│              Something Went Wrong                   │
│                                                     │
│        The server encountered an error.             │
│              Please try again.                      │
│                                                     │
│  Error Code: 503                                    │
│  Service Temporarily Unavailable                   │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │              [Try Again]                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  [Report Issue]                  [Contact Support] │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 6. NOTIFICATION & FEEDBACK STATES

### 6.1 Toast Notifications

```
Success:
┌────────────────────────────────────┐
│ ✓ Message copied to clipboard      │
└────────────────────────────────────┘

Error:
┌─────────────────────────────────────────────┐
│ ✕ Failed to send message - Retry?      [↻]  │
└─────────────────────────────────────────────┘

Warning:
┌────────────────────────────────────┐
│ ⚠ Trade requires approval          │
└────────────────────────────────────┘

Info:
┌────────────────────────────────────┐
│ ℹ New model available - Update?    │
└────────────────────────────────────┘
```

---

## 7. INTERACTION ANIMATIONS

### 7.1 Message Streaming

```
1. User submits message
2. Input field clears, message appears in chat
3. AI response starts with loading spinner
4. Characters stream in one by one (50-100ms each)
5. Action buttons appear when complete
```

### 7.2 Button States

```
Default:      [Send]
Hover:        [Send] (slightly darker, shadow)
Active:       [Send] (pressed appearance)
Loading:      [⟳ Sending...]
Disabled:     [Send] (grayed out)
Success:      [✓ Sent] (green)
```

### 7.3 Slide Transitions

```
Page enter:   Fade in + slide up (300ms)
Page exit:    Fade out + slide down (200ms)
Modal open:   Scale in + fade (200ms)
Modal close:  Scale out + fade (150ms)
```

---

## 8. COLOR USAGE IN CONTEXT

### Status Colors
```
Success (Green #0F6E56):
- Completed actions
- Valid inputs
- Successful trades
- Status indicators (active)

Error (Red #E5484D):
- Failed actions
- Invalid inputs
- Warnings
- Losses/negative P&L

Warning (Amber #854F0B):
- Pending actions
- Requires attention
- Risky trades

Info (Blue #2B63C7):
- Informational messages
- Helpful hints
- Neutral status
```

### Semantic Usage
```
Neural Purple (#7C51DC): Primary actions, AI features
Deep Blue (#2B63C7): Secondary actions, navigation
Neutral Gray (#1A1816): Text, supporting elements
White (#FFFFFF): Backgrounds, surfaces
```

---

This comprehensive UI design guide ensures consistent, beautiful, and accessible interfaces across ShivaAI Jarvis. All screens follow the design system tokens and can be implemented using the React component library provided.

