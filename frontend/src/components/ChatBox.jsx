import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, MessageSquare, ShieldAlert } from 'lucide-react';
import { apiService } from '../services/api';
import Message from './Message';

export const ChatBox = ({ 
  currentSessionId, 
  selectedDocIds, 
  documents,
  onNewSessionCreated, 
  messages, 
  setMessages,
  geminiStatus
}) => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessageText = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // 1. Add user message locally
    const tempUserMsg = {
      role: 'user',
      content: userMessageText,
      timestamp: new Date().toISOString(),
      sources: null
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      // 2. Query RAG backend
      const response = await apiService.askQuestion(
        userMessageText,
        currentSessionId,
        selectedDocIds
      );

      // 3. Update parent with the returned session ID if we were in a temporary session
      if (!currentSessionId && response.session_id) {
        if (onNewSessionCreated) {
          onNewSessionCreated(response.session_id);
        }
      }

      // 4. Add AI response locally
      const tempAiMsg = {
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toISOString(),
        sources: response.sources
      };
      setMessages(prev => [...prev, tempAiMsg]);

    } catch (err) {
      console.error(err);
      const errorMsg = {
        role: 'assistant',
        content: `Error: ${typeof err === 'string' ? err : 'Unable to contact the AI assistant. Please try again later.'}`,
        timestamp: new Date().toISOString(),
        sources: []
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to count active documents filtered
  const activeDocCount = selectedDocIds.length;
  const filterSummary = activeDocCount === 0 
    ? "Searching across all uploaded documents" 
    : `Searching across ${activeDocCount} selected document(s)`;

  return (
    <div className="flex flex-col h-full rounded-xl border border-slate-800 bg-slate-950/30 overflow-hidden shadow-2xl">
      
      {/* Top Info Banner */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/60 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <Sparkles size={14} className="text-violet-400" />
          <span>{filterSummary}</span>
        </div>
        
        {/* Offline Alert */}
        {geminiStatus === 'disconnected' && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] animate-pulse">
            <ShieldAlert size={12} />
            <span>AI Assistant Offline</span>
          </div>
        )}
      </div>

      {/* Messages Scrolling Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 animate-fade-in">
            <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-full text-slate-500 mb-4 shadow-lg">
              <MessageSquare size={36} className="text-violet-500" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">
              Start chatting with your documents!
            </h3>
            <p className="text-xs text-slate-500 max-w-[280px] leading-relaxed">
              Ask questions about contracts, policy manuals, reports, or compare details. Ensure documents are checked in the sidebar.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <Message key={index} message={msg} />
          ))
        )}

        {/* AI Typing Loader */}
        {isLoading && (
          <div className="flex w-full gap-3 justify-start items-start animate-fade-in">
            <div className="flex items-center justify-center w-8 h-8 rounded-full border border-violet-500/30 bg-violet-950/40 text-violet-400 shrink-0">
              <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce mx-0.5" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            
            <div className="p-4 rounded-2xl rounded-tl-none bg-violet-950/15 border border-violet-900/20 text-xs text-violet-300 italic">
              AI is searching semantic chunks and composing answer...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Controls */}
      <form onSubmit={handleSend} className="p-3 bg-slate-900/40 border-t border-slate-800 flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={isLoading || documents.length === 0}
          placeholder={
            documents.length === 0 
              ? "Upload a document in the sidebar to start..." 
              : "Ask a question about the active document(s)..."
          }
          className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all font-sans disabled:opacity-50"
        />
        
        <button
          type="submit"
          disabled={!inputValue.trim() || isLoading || documents.length === 0}
          className="flex items-center justify-center w-11 h-11 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:bg-slate-800 text-white disabled:text-slate-500 shadow-lg hover:shadow-violet-600/20 transition-all cursor-pointer shrink-0"
        >
          <Send size={16} />
        </button>
      </form>
      
    </div>
  );
};

export default ChatBox;
