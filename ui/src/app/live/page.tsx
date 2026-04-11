"use client";

import { useState, useEffect, useRef } from "react";
type TranscriptLine = {
  timestamp: string;
  speaker: string;
  text: string;
  trigger?: {
    claimId: string;
    metric: string;
    guidedValue: string;
    actualValue: string;
    delta: string;
    flag: "BEAT" | "MISS" | "IN-LINE";
    pattern?: string;
    sourceGuidance: string;
    sourceActual: string;
    confidenceLanguage: string;
  };
};

// Simulated earnings call transcript with triggers
const simulatedTranscript: TranscriptLine[] = [
  { timestamp: "00:00", speaker: "Operator", text: "Good afternoon, ladies and gentlemen. Welcome to IHCL's Q2 FY24 Earnings Conference Call." },
  { timestamp: "00:15", speaker: "Operator", text: "We have with us today Mr. Puneet Chhatwal, Managing Director and CEO, and Mr. Giridhar Sanjeevi, CFO." },
  { timestamp: "00:32", speaker: "Operator", text: "I would now like to hand the conference over to Mr. Chhatwal. Over to you, sir." },
  { timestamp: "01:05", speaker: "CEO", text: "Thank you. Good afternoon, everyone. I'm pleased to share our Q2 results which reflect strong momentum across our portfolio." },
  { timestamp: "01:28", speaker: "CEO", text: "Our consolidated revenue grew 16.2% year-over-year to INR 6,768 crores, driven by robust demand across both domestic and international markets." },
  { timestamp: "02:15", speaker: "CEO", text: "The Indian hotel sector continues to benefit from a structural tourism upcycle. Corporate travel has fully recovered and leisure demand remains elevated." },
  { timestamp: "03:01", speaker: "CEO", text: "Across our luxury portfolio, particularly the Taj brand, we are seeing unprecedented demand levels. Wedding and MICE segments are showing exceptional growth." },
  {
    timestamp: "03:45",
    speaker: "CEO",
    text: "We expect RevPAR to grow 15% in FY25 driven by strong demand across our luxury portfolio.",
    trigger: {
      claimId: "1",
      metric: "RevPAR Growth",
      guidedValue: "15% growth",
      actualValue: "9.2% growth",
      delta: "-5.8pp",
      flag: "MISS",
      pattern: "3rd consecutive quarter of guidance miss on RevPAR",
      sourceGuidance: "Q2 FY24 Earnings Call | 12:41",
      sourceActual: "AR FY25 | Page 87",
      confidenceLanguage: "EXPECT",
    },
  },
  { timestamp: "04:22", speaker: "CEO", text: "Our brand portfolio is well-positioned. Taj continues to be the strongest luxury brand in India. Vivanta is scaling rapidly in the premium space." },
  { timestamp: "05:10", speaker: "CEO", text: "We are taking pricing across all properties — our premium positioning gives us that leverage." },
  {
    timestamp: "05:35",
    speaker: "CEO",
    text: "We are taking pricing across all properties — our premium positioning gives us that leverage. Growth will be ADR-led.",
    trigger: {
      claimId: "3",
      metric: "RevPAR Driver (Occupancy vs ADR)",
      guidedValue: "ADR-led growth",
      actualValue: "Occupancy +8pp, ADR flat YoY",
      delta: "Mismatch",
      flag: "MISS",
      pattern: "Management claims ADR-led, but data shows occupancy-led growth",
      sourceGuidance: "Q3 FY24 Earnings Call | 14:02",
      sourceActual: "AR FY24 | Page 91",
      confidenceLanguage: "WILL",
    },
  },
  { timestamp: "06:20", speaker: "CEO", text: "On the expansion front, we have an aggressive pipeline. Our management contract model through Ginger is driving rapid scale." },
  {
    timestamp: "07:01",
    speaker: "CEO",
    text: "We will add 2,000 keys by FY26 across Taj, Vivanta and Ginger brands. This is a firm commitment.",
    trigger: {
      claimId: "2",
      metric: "New Room Additions",
      guidedValue: "2,000 keys",
      actualValue: "1,340 keys",
      delta: "-660 rooms",
      flag: "MISS",
      pattern: "Room addition shortfall — 3 years running",
      sourceGuidance: "Q1 FY24 Earnings Call | 08:15",
      sourceActual: "AR FY26 | Page 34",
      confidenceLanguage: "WILL",
    },
  },
  { timestamp: "07:45", speaker: "CEO", text: "Ginger is our fastest growing brand. We see tremendous potential in the lean luxe segment." },
  {
    timestamp: "08:12",
    speaker: "CEO",
    text: "Ginger is on track for INR 3,200 RevPAR in FY25 — it's our fastest growing brand.",
    trigger: {
      claimId: "8",
      metric: "Ginger Brand RevPAR",
      guidedValue: "₹3,200 RevPAR",
      actualValue: "₹3,450 RevPAR",
      delta: "+₹250",
      flag: "BEAT",
      pattern: undefined,
      sourceGuidance: "Q2 FY24 Earnings Call | 16:55",
      sourceActual: "AR FY25 | Page 44",
      confidenceLanguage: "EXPECT",
    },
  },
  { timestamp: "09:00", speaker: "CFO", text: "Thank you. Let me take you through the financial highlights." },
  { timestamp: "09:30", speaker: "CFO", text: "EBITDA margin for the quarter came in at 33.2%. Our cost optimization programs are delivering results." },
  {
    timestamp: "10:05",
    speaker: "CFO",
    text: "We are confident of sustaining 35%+ EBITDA margins going forward.",
    trigger: {
      claimId: "4",
      metric: "EBITDA Margin",
      guidedValue: "35%+ margin",
      actualValue: "33.2%",
      delta: "-1.8pp",
      flag: "MISS",
      pattern: "F&B share rising from 28% to 36% — compressing margins",
      sourceGuidance: "Q4 FY23 Earnings Call | 22:10",
      sourceActual: "AR FY24 | P&L Statement",
      confidenceLanguage: "CONFIDENT",
    },
  },
  { timestamp: "10:45", speaker: "CFO", text: "Our balance sheet continues to strengthen. We've made significant progress on deleveraging." },
  {
    timestamp: "11:15",
    speaker: "CFO",
    text: "Our target remains to become net debt-free by end of FY24.",
    trigger: {
      claimId: "5",
      metric: "Debt Reduction",
      guidedValue: "Net debt-free by FY24",
      actualValue: "Net debt: ₹312 Cr",
      delta: "Not achieved",
      flag: "MISS",
      pattern: undefined,
      sourceGuidance: "Q2 FY23 Earnings Call | 18:33",
      sourceActual: "AR FY24 | Balance Sheet | Page 72",
      confidenceLanguage: "TARGETING",
    },
  },
  { timestamp: "11:50", speaker: "CFO", text: "With that, I'd like to open the floor for questions." },
  { timestamp: "12:10", speaker: "Analyst", text: "Hi, this is from Motilal Oswal. Can you comment on your international expansion pipeline?" },
  {
    timestamp: "12:35",
    speaker: "CEO",
    text: "We plan to open 5 new international Taj properties by FY25, including London and Dubai.",
    trigger: {
      claimId: "7",
      metric: "International Expansion",
      guidedValue: "5 new international properties",
      actualValue: "3 properties opened",
      delta: "-2 properties",
      flag: "MISS",
      pattern: undefined,
      sourceGuidance: "Q3 FY23 Earnings Call | 31:05",
      sourceActual: "AR FY25 | Page 28",
      confidenceLanguage: "PLAN",
    },
  },
  { timestamp: "13:10", speaker: "CEO", text: "We remain very optimistic about IHCL's future. The structural tailwinds in Indian hospitality are strong." },
  { timestamp: "13:30", speaker: "Operator", text: "Thank you. That concludes today's earnings conference call." },
];

type Alert = {
  id: string;
  timestamp: string;
  trigger: NonNullable<TranscriptLine["trigger"]>;
  lineIndex: number;
};

export default function LivePage() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentLine, setCurrentLine] = useState(-1);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [credibilityMeter, setCredibilityMeter] = useState(80);
  const [speed, setSpeed] = useState<1 | 2 | 3>(1);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const missCount = alerts.filter((a) => a.trigger.flag === "MISS").length;
  const beatCount = alerts.filter((a) => a.trigger.flag === "BEAT").length;

  useEffect(() => {
    if (isPlaying && currentLine < simulatedTranscript.length - 1) {
      const delay = speed === 1 ? 2000 : speed === 2 ? 1000 : 500;
      intervalRef.current = setInterval(() => {
        setCurrentLine((prev) => {
          const next = prev + 1;
          if (next >= simulatedTranscript.length) {
            setIsPlaying(false);
            if (intervalRef.current) clearInterval(intervalRef.current);
            return prev;
          }

          const line = simulatedTranscript[next];
          if (line.trigger) {
            const newAlert: Alert = {
              id: line.trigger.claimId,
              timestamp: line.timestamp,
              trigger: line.trigger,
              lineIndex: next,
            };
            setAlerts((prev) => [...prev, newAlert]);

            if (line.trigger.flag === "MISS") {
              setCredibilityMeter((prev) => Math.max(0, prev - 8));
            } else if (line.trigger.flag === "BEAT") {
              setCredibilityMeter((prev) => Math.min(100, prev + 3));
            }
          }

          return next;
        });
      }, delay);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, currentLine, speed]);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      const activeEl = transcriptRef.current.querySelector(`[data-line="${currentLine}"]`);
      activeEl?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [currentLine]);

  const reset = () => {
    setIsPlaying(false);
    setCurrentLine(-1);
    setAlerts([]);
    setCredibilityMeter(80);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const meterColor =
    credibilityMeter >= 70 ? "#16a34a" :
    credibilityMeter >= 50 ? "#f59e0b" : "#dc2626";

  return (
    <div className="min-h-screen bg-[#0f172a] text-white">
      {/* Header */}
      <div className="border-b border-[#1e293b] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-[11px] tracking-[0.2em] uppercase text-[#64748b] font-medium">
              EquityLens AI — Live Monitor
            </p>
            <h1 className="text-lg font-semibold text-white mt-1">
              Earnings Call Lie Detector
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              {([1, 2, 3] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  className={`px-2 py-1 text-[10px] font-mono rounded cursor-pointer ${
                    speed === s ? "bg-white text-[#0f172a]" : "text-[#64748b] hover:text-white"
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>
            <button
              onClick={() => isPlaying ? setIsPlaying(false) : (currentLine === -1 || currentLine >= simulatedTranscript.length - 1 ? (reset(), setTimeout(() => { setIsPlaying(true); setCurrentLine(0); }, 100)) : setIsPlaying(true))}
              className={`px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-colors ${
                isPlaying
                  ? "bg-amber-500 hover:bg-amber-600 text-black"
                  : "bg-white hover:bg-gray-100 text-[#0f172a]"
              }`}
            >
              {isPlaying ? "Pause" : currentLine >= simulatedTranscript.length - 1 ? "Replay" : "Start Simulation"}
            </button>
            <a
              href="/"
              className="px-3 py-2 text-sm text-[#64748b] hover:text-white transition-colors"
            >
              Back
            </a>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Stats bar */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {/* Credibility Meter */}
          <div className="bg-[#1e293b] rounded-lg p-4 col-span-1">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#64748b] mb-2">
              Live Credibility
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-bold" style={{ color: meterColor }}>
                {credibilityMeter}
              </span>
              <span className="text-sm text-[#64748b]">/100</span>
            </div>
            <div className="w-full h-2 bg-[#0f172a] rounded-full mt-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${credibilityMeter}%`, backgroundColor: meterColor }}
              />
            </div>
          </div>

          <div className="bg-[#1e293b] rounded-lg p-4">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#64748b] mb-2">
              Claims Detected
            </p>
            <span className="text-3xl font-mono font-bold text-white">{alerts.length}</span>
          </div>

          <div className="bg-[#1e293b] rounded-lg p-4">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#64748b] mb-2">
              Contradictions
            </p>
            <span className="text-3xl font-mono font-bold text-red-400">{missCount}</span>
          </div>

          <div className="bg-[#1e293b] rounded-lg p-4">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#64748b] mb-2">
              Confirmed
            </p>
            <span className="text-3xl font-mono font-bold text-emerald-400">{beatCount}</span>
          </div>
        </div>

        {/* Main layout: transcript + alerts */}
        <div className="grid grid-cols-5 gap-6">
          {/* Transcript — left 3 cols */}
          <div className="col-span-3 bg-[#1e293b] rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-[#0f172a] flex items-center gap-2">
              {isPlaying && (
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              )}
              <span className="text-xs text-[#64748b] font-medium">
                {isPlaying ? "LIVE — IHCL Q2 FY24 Earnings Call" : "IHCL Q2 FY24 Earnings Call (Simulated)"}
              </span>
            </div>
            <div ref={transcriptRef} className="max-h-[60vh] overflow-y-auto p-4 space-y-1">
              {currentLine === -1 ? (
                <p className="text-sm text-[#475569] text-center py-10">
                  Press &ldquo;Start Simulation&rdquo; to begin the earnings call analysis
                </p>
              ) : (
                simulatedTranscript.slice(0, currentLine + 1).map((line, i) => {
                  const hasAlert = line.trigger;
                  const isCurrent = i === currentLine;
                  return (
                    <div
                      key={i}
                      data-line={i}
                      className={`flex gap-3 py-2 px-3 rounded-lg transition-all ${
                        hasAlert
                          ? line.trigger!.flag === "MISS"
                            ? "bg-red-950/30 border border-red-900/30"
                            : "bg-emerald-950/30 border border-emerald-900/30"
                          : isCurrent
                            ? "bg-[#0f172a]/50"
                            : ""
                      }`}
                    >
                      <span className="text-[10px] font-mono text-[#475569] w-10 shrink-0 pt-0.5">
                        {line.timestamp}
                      </span>
                      <div className="flex-1 min-w-0">
                        <span className={`text-[11px] font-semibold mr-2 ${
                          line.speaker === "CEO" ? "text-blue-400" :
                          line.speaker === "CFO" ? "text-amber-400" :
                          line.speaker === "Analyst" ? "text-purple-400" :
                          "text-[#475569]"
                        }`}>
                          {line.speaker}
                        </span>
                        <span className={`text-[13px] leading-relaxed ${
                          hasAlert ? "text-white font-medium" : "text-[#94a3b8]"
                        }`}>
                          {line.text}
                        </span>
                        {hasAlert && (
                          <span className={`inline-block ml-2 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                            line.trigger!.flag === "MISS"
                              ? "bg-red-500 text-white"
                              : "bg-emerald-500 text-white"
                          }`}>
                            {line.trigger!.flag === "MISS" ? "CONTRADICTION" : "CONFIRMED"}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Alerts — right 2 cols */}
          <div className="col-span-2 space-y-3 max-h-[70vh] overflow-y-auto">
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#64748b] font-medium mb-2">
              Real-Time Alerts
            </p>

            {alerts.length === 0 ? (
              <div className="bg-[#1e293b] rounded-lg p-6 text-center">
                <p className="text-sm text-[#475569]">
                  Alerts will appear here as the system detects claims
                </p>
              </div>
            ) : (
              [...alerts].reverse().map((alert) => (
                <div
                  key={alert.id}
                  className={`rounded-lg p-4 border-l-4 animate-in ${
                    alert.trigger.flag === "MISS"
                      ? "bg-red-950/20 border-l-red-500"
                      : alert.trigger.flag === "BEAT"
                        ? "bg-emerald-950/20 border-l-emerald-500"
                        : "bg-blue-950/20 border-l-blue-500"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${
                      alert.trigger.flag === "MISS"
                        ? "bg-red-500 text-white"
                        : "bg-emerald-500 text-white"
                    }`}>
                      {alert.trigger.flag}
                    </span>
                    <span className="text-[10px] font-mono text-[#64748b]">
                      {alert.trigger.confidenceLanguage}
                    </span>
                    <span className="text-[10px] font-mono text-[#475569]">
                      @{alert.timestamp}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-white mb-2">
                    {alert.trigger.metric}
                  </p>

                  <div className="grid grid-cols-3 gap-2 mb-2 text-xs">
                    <div>
                      <span className="text-[#64748b] block">Guided</span>
                      <span className="font-mono text-white">{alert.trigger.guidedValue}</span>
                    </div>
                    <div>
                      <span className="text-[#64748b] block">Actual</span>
                      <span className="font-mono text-white">{alert.trigger.actualValue}</span>
                    </div>
                    <div>
                      <span className="text-[#64748b] block">Delta</span>
                      <span className={`font-mono font-bold ${
                        alert.trigger.flag === "MISS" ? "text-red-400" : "text-emerald-400"
                      }`}>{alert.trigger.delta}</span>
                    </div>
                  </div>

                  {alert.trigger.pattern && (
                    <p className="text-[11px] text-amber-400 bg-amber-950/30 rounded px-2 py-1 mb-2">
                      {alert.trigger.pattern}
                    </p>
                  )}

                  <div className="text-[10px] text-[#475569] space-y-0.5">
                    <p>Guidance: [{alert.trigger.sourceGuidance}]</p>
                    <p>Actual: [{alert.trigger.sourceActual}]</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
