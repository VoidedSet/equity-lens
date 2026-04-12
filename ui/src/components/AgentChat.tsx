"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import { 
  SendHorizontal, 
  Brain, 
  Terminal, 
  Bot, 
  User, 
  Loader2,
  Sparkles,
  BarChart4,
  Check,
  X
} from "lucide-react";

type MessageRole = "user" | "assistant";

interface ThoughtBlock {
  id: string;
  type: "status" | "thought" | "tool" | "result" | "error" | "charts";
  content?: string;
  tool?: string;
  args?: any;
  paths?: string[];
}

interface Message {
  id: string;
  role: MessageRole;
  text: string;
  thoughts: ThoughtBlock[];
  isStreaming: boolean;
}

interface AgentChatProps {
  onClose?: () => void;
}

export default function AgentChat({ onClose }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isProcessing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isProcessing) return;

    const query = inputValue.trim();
    setInputValue("");
    
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: query,
      thoughts: [],
      isStreaming: false
    };

    const asstMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      text: "",
      thoughts: [],
      isStreaming: true
    };

    setMessages((prev) => [...prev, userMsg, asstMsg]);
    setIsProcessing(true);

    try {
      const history = messages.map(m => ({
        role: m.role,
        content: m.text
      }));

      const res = await fetch("http://localhost:8001/agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, history })
      });

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              
              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIndex = newMsgs.length - 1;
                const last = { 
                  ...newMsgs[lastIndex], 
                  thoughts: [...newMsgs[lastIndex].thoughts] 
                };
                newMsgs[lastIndex] = last;
                
                if (data.type === "result") {
                  last.text = data.content;
                  last.isStreaming = false;
                } else if (data.type === "error") {
                  last.text += `\n\n**Error:** ${data.message}`;
                  last.isStreaming = false;
                } else if (data.type === "charts") {
                   last.thoughts.push({
                      id: Math.random().toString(),
                      type: "charts",
                      paths: data.paths
                   });
                } else {
                  last.thoughts.push({
                    id: Math.random().toString(),
                    type: data.type,
                    content: data.message || data.thought,
                    tool: data.tool,
                    args: data.args
                  });
                }
                
                return newMsgs;
              });
            } catch (err) {
              console.error("Parse error:", err, dataStr);
            }
          }
        }
      }
    } catch (error: any) {
      console.error(error);
      setMessages(prev => {
        const newMsgs = [...prev];
        const last = newMsgs[newMsgs.length - 1];
        last.text = `Error connecting to agent: ${error.message}`;
        last.isStreaming = false;
        return newMsgs;
      });
    } finally {
      setIsProcessing(false);
      setMessages(prev => {
        const newMsgs = [...prev];
        const last = newMsgs[newMsgs.length - 1];
        if (last && last.isStreaming) last.isStreaming = false;
        return newMsgs;
      });
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-[var(--bg)] relative">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-gray-50/50">
        <div className="flex items-center">
          <Sparkles className="w-5 h-5 mr-2 text-[var(--fg)]" />
          <h2 className="font-serif font-medium text-lg">AI Research Desk</h2>
        </div>
        {onClose && (
          <button 
            onClick={onClose} 
            className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-200 rounded-md transition-colors"
            title="Close workspace"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[var(--muted)] space-y-4">
            <Brain className="w-12 h-12 opacity-50" />
            <p className="font-serif text-lg text-center max-w-sm">
              Ask about financial trends, peer comparisons, or specific metrics for Indian Hotels, Chalet, Lemon Tree, EIH, or Juniper.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col w-full min-w-0 ${msg.role === "user" ? "items-end" : "items-start"}`}>
            
            <div className={`flex w-full min-w-0 max-w-[95%] md:max-w-[85%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
              {/* Avatar */}
              <div className={`mt-1 flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full ${msg.role === "user" ? "bg-[var(--fg)] text-[var(--bg)] ml-3" : "border border-[var(--border)] bg-white text-[var(--fg)] mr-3"}`}>
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>

              {/* Message Content */}
              <div className={`flex flex-col flex-1 min-w-0 w-full ${msg.role === "user" ? "items-end" : "items-start"}`}>
                
                {msg.role === "assistant" && msg.thoughts.length > 0 && (
                  <div className="w-full mb-3 space-y-2 font-mono text-sm">
                    <AnimatePresence>
                      {msg.thoughts.map((th, index) => {
                        const isLast = index === msg.thoughts.length - 1;
                        return (
                        <motion.div
                          initial={{ opacity: 0, y: 5 }}
                          animate={{ opacity: 1, y: 0 }}
                          key={th.id}
                          className="bg-gray-50 border border-[var(--border)] p-3 rounded-md text-[var(--fg)] shadow-sm max-w-full overflow-hidden"
                        >
                          {th.type === "status" && (
                            <div className="flex items-center text-[var(--muted)]">
                              {msg.isStreaming && isLast ? (
                                <Loader2 className="w-3 h-3 mr-2 animate-spin text-blue-500" />
                              ) : (
                                <Check className="w-3 h-3 mr-2 text-green-500" />
                              )}
                              {th.content}
                            </div>
                          )}
                          
                          {th.type === "thought" && (
                            <div className="flex flex-col space-y-2">
                              <div className="flex items-start">
                                <Brain className="w-4 h-4 mr-2 mt-0.5 text-blue-600 flex-shrink-0" />
                                <span className="text-gray-700">{th.content}</span>
                              </div>
                              {th.tool && (
                                <div className="ml-6 flex items-start text-xs bg-gray-100 p-2 rounded border border-gray-200">
                                  <Terminal className="w-3 h-3 mr-1 mt-0.5 text-gray-500 flex-shrink-0" />
                                  <span className="font-semibold">{th.tool}</span>
                                  <span className="text-gray-500 ml-2 overflow-x-auto whitespace-pre">
                                    {JSON.stringify(th.args)}
                                  </span>
                                </div>
                              )}
                            </div>
                          )}

                          {th.type === "charts" && th.paths && (
                            <div className="flex flex-col space-y-3 mt-3 border-t pt-3 border-[var(--border)]">
                               <div className="flex items-center text-green-700 font-semibold mb-1 text-sm bg-green-50 w-max px-2 py-1 rounded">
                                  <BarChart4 className="w-4 h-4 mr-2" />
                                  Generated Charts
                               </div>
                               <div className="grid grid-cols-1 gap-4 w-full">
                                 {th.paths.map((p, i) => {
                                    const filename = p.split(/[\/\\]/).pop();
                                    return (
                                      <div key={i} className="flex flex-col bg-white border border-gray-200 p-2 rounded shadow-sm">
                                        <img 
                                          src={`http://localhost:8001/output/${filename}`} 
                                          alt={filename || "generated chart"} 
                                          className="w-full h-auto max-h-[400px] object-contain rounded"
                                        />
                                        <div className="text-xs text-gray-500 mt-2 font-sans truncate" title={filename}>{filename}</div>
                                      </div>
                                    );
                                 })}
                               </div>
                            </div>
                          )}
                        </motion.div>
                      )})}
                    </AnimatePresence>
                  </div>
                )}

                {/* Final Text */}
                {(msg.text || (msg.isStreaming && msg.thoughts.length === 0)) && (
                  <div className={`p-5 min-w-0 max-w-full overflow-hidden ${
                    msg.role === "user" 
                      ? "bg-[var(--fg)] text-[var(--bg)] rounded-[20px] rounded-tr-md" 
                      : "bg-white border border-[var(--border)] text-[var(--fg)] rounded-[20px] rounded-tl-md shadow-sm"
                  }`}>
                    {msg.isStreaming && !msg.text ? (
                      <div className="flex space-x-1 items-center h-6">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                      </div>
                    ) : (
                      <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none break-words whitespace-pre-wrap [&_pre]:overflow-x-auto [&_pre]:max-w-[80vw] md:[&_pre]:max-w-[700px] [&_img]:max-w-full">
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-[var(--border)] bg-white">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isProcessing}
            placeholder={isProcessing ? "Agent is typing..." : "Ask the financial agent a question..."}
            className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-[var(--border)] focus:outline-none focus:border-[var(--fg)] transition-colors placeholder:text-gray-400 font-sans"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className="absolute right-2 p-2 text-[var(--fg)] hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
          >
            <SendHorizontal size={20} />
          </button>
        </form>
        <div className="mt-2 text-center">
          <span className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-medium">
            Powered by Groq & Supabase Knowledge Graph
          </span>
        </div>
      </div>
    </div>
  );
}
