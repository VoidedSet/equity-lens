import React from "react";
import AgentChat from "@/components/AgentChat";

export const metadata = {
  title: "Agentic AI Analyst | The Big Leagues",
  description: "Interact with our Financial AI Agent.",
};

export default function AgentPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] flex flex-col items-center">
      
      {/* Editorial Header */}
      <section className="ed-section-ruled">
        <div className="ed-container">
          <div className="mb-4 text-center">
            <span className="kicker">Artificial Intelligence</span>
          </div>
          <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl text-[var(--fg)] font-bold text-center mb-6 leading-tight">
            Financial Agentic Analyst
          </h1>
          <p className="font-sans text-lg md:text-xl text-[var(--muted)] text-center max-w-2xl mx-auto mb-12">
            Ask complex financial queries. Watch the AI select the right tools, execute analysis, and synthesize data in real-time.
          </p>
          
          <div className="flex justify-center w-full">
            <AgentChat />
          </div>
        </div>
      </section>

    </div>
  );
}
