import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, User, Cpu } from 'lucide-react';

export const Message = ({ message }) => {
  const { role, content, sources, timestamp } = message;
  const isUser = role === 'user';
  const [expandedSourceIdx, setExpandedSourceIdx] = useState(null);

  // Helper to format timestamps nicely (HH:MM)
  const formatTime = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '';
    }
  };

  // Simple formatter for markdown bold **text** and lists
  const renderMessageContent = (text) => {
    if (!text) return '';
    
    // Split by newlines to render paragraphs
    const paragraphs = text.split('\n');
    return paragraphs.map((para, pIdx) => {
      if (!para.trim()) return <div key={pIdx} className="h-2"></div>;

      // Handle simple bullet points
      const isBullet = para.trim().startsWith('-') || para.trim().startsWith('*');
      const cleanText = isBullet ? para.trim().substring(1).trim() : para;

      // Replace bold markdown **word** with strong tags
      const parts = cleanText.split(/(\*\*.*?\*\*)/g);
      const renderedText = parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={idx} className="text-white font-bold">{part.slice(2, -2)}</strong>;
        }
        
        // Render citation links like [1], [2] as glowing inline pills
        const citationParts = part.split(/(\[\d+\])/g);
        return citationParts.map((cPart, cIdx) => {
          if (cPart.match(/^\[\d+\]$/)) {
            const num = parseInt(cPart.slice(1, -1));
            return (
              <span 
                key={cIdx} 
                onClick={() => setExpandedSourceIdx(expandedSourceIdx === num - 1 ? null : num - 1)}
                className="inline-block mx-0.5 px-1.5 py-0.5 rounded text-xs font-bold bg-violet-500/20 text-violet-300 border border-violet-500/35 cursor-pointer hover:bg-violet-500/40 hover:text-white transition-all shadow-sm"
              >
                {cPart}
              </span>
            );
          }
          return cPart;
        });
      });

      if (isBullet) {
        return (
          <li key={pIdx} className="ml-5 list-disc mb-1 text-slate-200">
            {renderedText}
          </li>
        );
      }

      return (
        <p key={pIdx} className="mb-2 leading-relaxed text-slate-200 text-sm md:text-base">
          {renderedText}
        </p>
      );
    });
  };

  return (
    <div className={`flex w-full gap-3 mb-4 animate-fade-in ${isUser ? 'justify-end' : 'justify-start'}`}>
      
      {/* AI Avatar */}
      {!isUser && (
        <div className="flex items-center justify-center w-8 h-8 rounded-full border border-violet-500/30 bg-violet-950/40 text-violet-400 shrink-0 shadow-lg">
          <Cpu size={16} className="animate-pulse-glow" />
        </div>
      )}

      {/* Message Bubble */}
      <div className={`max-w-[85%] md:max-w-[75%] p-4 rounded-2xl glass-panel ${
        isUser 
          ? 'bg-slate-900/60 border-slate-700/40 rounded-tr-none' 
          : 'bg-violet-950/20 border-violet-900/30 rounded-tl-none'
      }`}>
        
        {/* Message Text */}
        <div className="text-slate-100">
          {isBulletList(content) ? (
            <ul className="space-y-1">{renderMessageContent(content)}</ul>
          ) : (
            renderMessageContent(content)
          )}
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-800/40 text-[10px] text-slate-500">
          <span>{isUser ? 'You' : 'Assistant'}</span>
          <span>{formatTime(timestamp)}</span>
        </div>

        {/* Source Citations */}
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-violet-950/40">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-violet-400 mb-2">
              <FileText size={13} />
              <span>Sources Used ({sources.length}):</span>
            </div>
            
            <div className="flex flex-wrap gap-1.5 mb-2">
              {sources.map((source, index) => {
                const isSelected = expandedSourceIdx === index;
                return (
                  <button
                    key={index}
                    onClick={() => setExpandedSourceIdx(isSelected ? null : index)}
                    className={`flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg border transition-all ${
                      isSelected 
                        ? 'bg-violet-500/25 border-violet-500 text-white font-medium' 
                        : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    <span className="font-bold">[{index + 1}]</span>
                    <span className="truncate max-w-[120px]">{source.filename}</span>
                    <span className="text-[9px] opacity-75">(p. {source.page})</span>
                    {isSelected ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                  </button>
                );
              })}
            </div>

            {/* Expanded Snippet Content */}
            {expandedSourceIdx !== null && sources[expandedSourceIdx] && (
              <div className="p-3 mt-2 text-xs rounded-lg bg-slate-950/50 border border-violet-950/60 text-slate-300 leading-relaxed font-sans max-h-[160px] overflow-y-auto animate-fade-in shadow-inner">
                <div className="font-semibold text-violet-400 mb-1 flex items-center justify-between">
                  <span>Snippet [{expandedSourceIdx + 1}]:</span>
                  <span className="text-[10px] text-slate-500">{sources[expandedSourceIdx].filename} - Page {sources[expandedSourceIdx].page}</span>
                </div>
                "{sources[expandedSourceIdx].text}"
              </div>
            )}
          </div>
        )}

      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex items-center justify-center w-8 h-8 rounded-full border border-slate-700/50 bg-slate-900/60 text-slate-300 shrink-0 shadow-lg">
          <User size={16} />
        </div>
      )}

    </div>
  );
};

// Helper function to check if string contains bullet format
const isBulletList = (text) => {
  if (!text) return false;
  return text.trim().startsWith('- ') || text.trim().startsWith('* ');
};

export default Message;
