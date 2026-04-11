// EquityLens AI — Hardcoded data for IHCL (Indian Hotels Company Ltd)
// This will be replaced with Supabase queries later

export type Company = {
  id: string;
  name: string;
  ticker: string;
  segment: string;
  strategy: string;
  brands: string[];
  keyMarkets: string[];
  color: string;
};

export type KeyMetric = {
  label: string;
  value: string;
  unit: string;
  change: number; // YoY %
  period: string;
};

export type GuidanceClaim = {
  id: string;
  metric: string;
  checkType: string;
  statementQuarter: string;
  targetPeriod: string;
  guidedValue: string;
  actualValue: string;
  delta: string;
  flag: "BEAT" | "MISS" | "IN-LINE";
  severity: "none" | "minor" | "moderate" | "major" | "critical";
  verbatimQuote: string;
  speaker: string;
  sourceGuidance: string;
  sourceActual: string;
  pattern?: string;
};

export type RiskFlag = {
  id: string;
  category: string;
  severity: "critical" | "high" | "medium";
  description: string;
  verbatimQuote?: string;
  source: string;
  period: string;
};

export type ScoreCard = {
  companyId: string;
  period: string;
  credibility: number;
  financialQuality: number;
  industryPosition: number;
  risk: number;
  composite: number;
};

export type CompanyCompareRow = {
  metric: string;
  unit: string;
  ihcl: string;
  chalet: string;
  lemonTree: string;
  eih: string;
  itcHotels: string;
};

// ─── Companies ────────────────────────────────────────────
export const companies: Company[] = [
  {
    id: "IHCL",
    name: "Indian Hotels Company Ltd",
    ticker: "INDHOTEL",
    segment: "Premium / Luxury",
    strategy: "Hybrid (Asset-Heavy + Management Contracts)",
    brands: ["Taj", "Vivanta", "SeleQtions", "Ginger"],
    keyMarkets: ["Mumbai", "Delhi", "Bengaluru", "Goa"],
    color: "#1e3a5f",
  },
  {
    id: "CHALET",
    name: "Chalet Hotels Ltd",
    ticker: "CHALET",
    segment: "Upper Midscale / Business",
    strategy: "Asset-Heavy",
    brands: ["Marriott", "Westin", "Renaissance", "Four Points"],
    keyMarkets: ["Mumbai", "Bengaluru", "Hyderabad"],
    color: "#6b4c9a",
  },
  {
    id: "LEMONTREE",
    name: "Lemon Tree Hotels Ltd",
    ticker: "LEMONTREE",
    segment: "Economy / Midscale",
    strategy: "Hybrid",
    brands: ["Lemon Tree Premier", "Lemon Tree", "Red Fox", "Keys"],
    keyMarkets: ["Delhi-NCR", "Hyderabad", "Pune", "Bengaluru"],
    color: "#2d8544",
  },
  {
    id: "EIH",
    name: "EIH Ltd (Oberoi Group)",
    ticker: "EIHOTEL",
    segment: "Luxury",
    strategy: "Asset-Heavy",
    brands: ["Oberoi", "Trident"],
    keyMarkets: ["Delhi", "Mumbai", "Udaipur", "Agra"],
    color: "#8b6914",
  },
  {
    id: "ITCHOTELS",
    name: "ITC Hotels Ltd",
    ticker: "ITCHOTELS",
    segment: "Premium Luxury",
    strategy: "Asset-Heavy",
    brands: ["ITC Grand", "Welcomhotel", "Mementos", "Storii"],
    keyMarkets: ["Delhi", "Bengaluru", "Chennai", "Kolkata"],
    color: "#1a6b6b",
  },
];

// ─── IHCL Key Metrics ─────────────────────────────────────
export const ihclKeyMetrics: KeyMetric[] = [
  { label: "RevPAR", value: "8,542", unit: "INR", change: 12.3, period: "FY24" },
  { label: "Occupancy", value: "72.1", unit: "%", change: 3.8, period: "FY24" },
  { label: "ADR", value: "11,847", unit: "INR", change: 8.1, period: "FY24" },
  { label: "Revenue", value: "6,768", unit: "INR Cr", change: 16.2, period: "FY24" },
  { label: "EBITDA Margin", value: "33.2", unit: "%", change: 1.4, period: "FY24" },
  { label: "Room Count", value: "28,475", unit: "keys", change: 9.1, period: "FY24" },
];

// ─── Said vs Delivered (Deviation Tracker) ─────────────────
export const ihclDeviations: GuidanceClaim[] = [
  {
    id: "1",
    metric: "RevPAR Growth",
    checkType: "Check 1: RevPAR",
    statementQuarter: "Q2 FY24",
    targetPeriod: "FY25",
    guidedValue: "15% growth",
    actualValue: "9.2% growth",
    delta: "-5.8pp",
    flag: "MISS",
    severity: "moderate",
    verbatimQuote: "We expect RevPAR to grow 15% in FY25 driven by strong demand across our luxury portfolio.",
    speaker: "CEO",
    sourceGuidance: "Q2 FY24 Earnings Call | 12:41",
    sourceActual: "AR FY25 | Page 87",
    pattern: "3rd consecutive quarter of guidance miss on RevPAR",
  },
  {
    id: "2",
    metric: "New Room Additions",
    checkType: "Check 2: Keys",
    statementQuarter: "Q1 FY24",
    targetPeriod: "FY26",
    guidedValue: "2,000 keys",
    actualValue: "1,340 keys",
    delta: "-660 rooms",
    flag: "MISS",
    severity: "major",
    verbatimQuote: "We will add 2,000 keys by FY26 across Taj, Vivanta and Ginger brands.",
    speaker: "MD",
    sourceGuidance: "Q1 FY24 Earnings Call | 08:15",
    sourceActual: "AR FY26 | Page 34",
    pattern: "Room addition shortfall — 3 years running",
  },
  {
    id: "3",
    metric: "RevPAR Driver (Occupancy vs ADR)",
    checkType: "Check 3: Driver Mismatch",
    statementQuarter: "Q3 FY24",
    targetPeriod: "FY24",
    guidedValue: "ADR-led growth",
    actualValue: "Occupancy +8pp, ADR flat YoY",
    delta: "Mismatch",
    flag: "MISS",
    severity: "moderate",
    verbatimQuote: "We are taking pricing across all properties — our premium positioning gives us that leverage.",
    speaker: "CEO",
    sourceGuidance: "Q3 FY24 Earnings Call | 14:02",
    sourceActual: "AR FY24 | Page 91",
    pattern: "Management claims ADR-led, but data shows occupancy-led growth",
  },
  {
    id: "4",
    metric: "EBITDA Margin",
    checkType: "Check 4: F&B Mix",
    statementQuarter: "Q4 FY23",
    targetPeriod: "FY24",
    guidedValue: "35%+ margin",
    actualValue: "33.2%",
    delta: "-1.8pp",
    flag: "MISS",
    severity: "minor",
    verbatimQuote: "We are confident of sustaining 35%+ EBITDA margins going forward.",
    speaker: "CFO",
    sourceGuidance: "Q4 FY23 Earnings Call | 22:10",
    sourceActual: "AR FY24 | P&L Statement",
    pattern: "F&B share rising from 28% to 36% — compressing margins",
  },
  {
    id: "5",
    metric: "Debt Reduction",
    checkType: "Check 5: Debt",
    statementQuarter: "Q2 FY23",
    targetPeriod: "FY24",
    guidedValue: "Net debt-free by FY24",
    actualValue: "Net debt: ₹312 Cr",
    delta: "Not achieved",
    flag: "MISS",
    severity: "minor",
    verbatimQuote: "Our target remains to become net debt-free by end of FY24.",
    speaker: "CFO",
    sourceGuidance: "Q2 FY23 Earnings Call | 18:33",
    sourceActual: "AR FY24 | Balance Sheet | Page 72",
  },
  {
    id: "6",
    metric: "Revenue Growth",
    checkType: "Check 1: RevPAR",
    statementQuarter: "Q1 FY24",
    targetPeriod: "FY24",
    guidedValue: "18-20% revenue growth",
    actualValue: "16.2% growth",
    delta: "-1.8pp to -3.8pp",
    flag: "IN-LINE",
    severity: "none",
    verbatimQuote: "We are guiding for 18-20% revenue growth in FY24.",
    speaker: "CEO",
    sourceGuidance: "Q1 FY24 Earnings Call | 05:22",
    sourceActual: "AR FY24 | Page 12",
  },
  {
    id: "7",
    metric: "International Expansion",
    checkType: "Check 2: Keys",
    statementQuarter: "Q3 FY23",
    targetPeriod: "FY25",
    guidedValue: "5 new international properties",
    actualValue: "3 properties opened",
    delta: "-2 properties",
    flag: "MISS",
    severity: "moderate",
    verbatimQuote: "We plan to open 5 new international Taj properties by FY25, including London and Dubai.",
    speaker: "MD",
    sourceGuidance: "Q3 FY23 Earnings Call | 31:05",
    sourceActual: "AR FY25 | Page 28",
  },
  {
    id: "8",
    metric: "Ginger Brand RevPAR",
    checkType: "Check 1: RevPAR",
    statementQuarter: "Q2 FY24",
    targetPeriod: "FY25",
    guidedValue: "₹3,200 RevPAR",
    actualValue: "₹3,450 RevPAR",
    delta: "+₹250",
    flag: "BEAT",
    severity: "none",
    verbatimQuote: "Ginger is on track for ₹3,200 RevPAR in FY25 — it's our fastest growing brand.",
    speaker: "CEO",
    sourceGuidance: "Q2 FY24 Earnings Call | 16:55",
    sourceActual: "AR FY25 | Page 44",
  },
];

// ─── Risk Flags ───────────────────────────────────────────
export const ihclRiskFlags: RiskFlag[] = [
  {
    id: "1",
    category: "Supply Overhang",
    severity: "high",
    description: "1,800 new 5-star keys under construction in Mumbai — IHCL derives 32% of revenue from Mumbai. Significant supply risk in core market.",
    verbatimQuote: "Mumbai accounts for approximately 32% of our consolidated room revenue.",
    source: "AR FY24 | Page 45 + Competitor DRHP | Page 88",
    period: "FY24-FY26",
  },
  {
    id: "2",
    category: "Margin Compression",
    severity: "high",
    description: "F&B revenue share rising steadily (28% → 36% over 4 years). F&B has lower margins than rooms, silently compressing EBITDA despite healthy RevPAR.",
    source: "AR FY21-FY24 | Revenue Notes",
    period: "FY21-FY24",
  },
  {
    id: "3",
    category: "Management Mismatch",
    severity: "medium",
    description: "3 consecutive quarters of RevPAR guidance miss. Management consistently over-projects pricing power. Claims ADR-led growth but actual data shows occupancy-driven.",
    source: "Earnings Calls Q1-Q3 FY24 vs AR FY24",
    period: "FY24",
  },
  {
    id: "4",
    category: "Operational",
    severity: "medium",
    description: "Room addition pipeline consistently under-delivers. Guided 2,000 keys by FY26, tracking at 1,340. Execution risk on expansion strategy.",
    source: "Q1 FY24 Call | 08:15 vs AR FY26 | Page 34",
    period: "FY24-FY26",
  },
];

// ─── 4-Dimension Scorecard ────────────────────────────────
export const ihclScorecard: ScoreCard = {
  companyId: "IHCL",
  period: "FY24",
  credibility: 58,
  financialQuality: 79,
  industryPosition: 88,
  risk: 65,
  composite: 71,
};

// ─── All Company Scorecards (for comparison) ──────────────
export const allScorecards: ScoreCard[] = [
  { companyId: "IHCL", period: "FY24", credibility: 58, financialQuality: 79, industryPosition: 88, risk: 65, composite: 71 },
  { companyId: "CHALET", period: "FY24", credibility: 72, financialQuality: 68, industryPosition: 62, risk: 55, composite: 65 },
  { companyId: "LEMONTREE", period: "FY24", credibility: 65, financialQuality: 61, industryPosition: 54, risk: 70, composite: 62 },
  { companyId: "EIH", period: "FY24", credibility: 81, financialQuality: 74, industryPosition: 71, risk: 78, composite: 76 },
  { companyId: "ITCHOTELS", period: "FY24", credibility: 69, financialQuality: 72, industryPosition: 66, risk: 73, composite: 70 },
];

// ─── Company Comparison Table ─────────────────────────────
export const companyCompare: CompanyCompareRow[] = [
  { metric: "RevPAR", unit: "INR", ihcl: "8,542", chalet: "6,180", lemonTree: "2,840", eih: "9,120", itcHotels: "7,650" },
  { metric: "Occupancy", unit: "%", ihcl: "72.1", chalet: "70.3", lemonTree: "68.4", eih: "69.8", itcHotels: "71.2" },
  { metric: "ADR", unit: "INR", ihcl: "11,847", chalet: "8,790", lemonTree: "4,152", eih: "13,066", itcHotels: "10,743" },
  { metric: "EBITDA Margin", unit: "%", ihcl: "33.2", chalet: "28.5", lemonTree: "22.1", eih: "36.4", itcHotels: "31.8" },
  { metric: "Revenue", unit: "INR Cr", ihcl: "6,768", chalet: "1,842", lemonTree: "1,036", eih: "1,892", itcHotels: "3,420" },
  { metric: "Room Count", unit: "keys", ihcl: "28,475", chalet: "5,420", lemonTree: "12,680", eih: "3,890", itcHotels: "11,200" },
  { metric: "Interest Coverage", unit: "x", ihcl: "4.2", chalet: "1.9", lemonTree: "2.8", eih: "6.1", itcHotels: "5.3" },
  { metric: "Credibility Score", unit: "/100", ihcl: "58", chalet: "72", lemonTree: "65", eih: "81", itcHotels: "69" },
];

// ─── RevPAR Trend Data (for chart) ───────────────────────
export const revparTrend = [
  { period: "FY21", IHCL: 3200, CHALET: 2400, LEMONTREE: 1100, EIH: 3600, ITCHOTELS: 2900 },
  { period: "FY22", IHCL: 5100, CHALET: 3800, LEMONTREE: 1650, EIH: 5400, ITCHOTELS: 4500 },
  { period: "FY23", IHCL: 7100, CHALET: 5200, LEMONTREE: 2350, EIH: 7800, ITCHOTELS: 6400 },
  { period: "FY24", IHCL: 8542, CHALET: 6180, LEMONTREE: 2840, EIH: 9120, ITCHOTELS: 7650 },
];

// ─── Credibility Trend ───────────────────────────────────
export const credibilityTrend = [
  { period: "FY21", score: 74 },
  { period: "FY22", score: 71 },
  { period: "FY23", score: 65 },
  { period: "FY24", score: 58 },
];

// ─── F&B Share Trend (for Check 4 visualization) ─────────
export const fnbShareTrend = [
  { period: "FY21", fnbShare: 28, ebitdaMargin: 32 },
  { period: "FY22", fnbShare: 30, ebitdaMargin: 31.5 },
  { period: "FY23", fnbShare: 33, ebitdaMargin: 29.8 },
  { period: "FY24", fnbShare: 36, ebitdaMargin: 33.2 },
];
