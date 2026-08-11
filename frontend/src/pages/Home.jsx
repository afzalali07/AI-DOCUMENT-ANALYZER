import React, { useState, useEffect } from 'react';
import { 
  FileText, MessageSquare, Plus, Trash2, LayoutDashboard, 
  Sparkles, Layers, ShieldCheck, ShieldAlert, BookOpen, Calendar, HelpCircle 
} from 'lucide-react';
import { apiService } from '../services/api';
import FileUpload from '../components/FileUpload';
import ChatBox from '../components/ChatBox';

export const Home = () => {
  // State variables
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'dashboard' | 'compare'
  
  // Dashboard & Comparison detail states
  const [focusedDocSummary, setFocusedDocSummary] = useState(null);
  const [compareSummaries, setCompareSummaries] = useState([]);
  
  // Health telemetry states
  const [backendHealth, setBackendHealth] = useState({
    status: 'checking',
    services: { sqlite: 'failed', chromadb: 'failed', gemini_api: 'disconnected' }
  });

  // Load initial configurations
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      // 1. Fetch backend health
      const health = await apiService.getHealth();
      setBackendHealth(health);

      // 2. Fetch documents
      const docs = await apiService.listDocuments();
      setDocuments(docs);

      // 3. Fetch chat sessions
      const chatSessions = await apiService.listSessions();
      setSessions(chatSessions);

      if (chatSessions.length > 0) {
        const firstSession = chatSessions[0].id;
        setCurrentSessionId(firstSession);
        // Load messages for the first session
        const history = await apiService.getSessionHistory(firstSession);
        setMessages(history);
      }
    } catch (error) {
      console.error("Failed to load initial RAG data:", error);
    }
  };

  // Telemetry poller (every 10 seconds)
  useEffect(() => {
    const interval = setInterval(async () => {
      const health = await apiService.getHealth();
      setBackendHealth(health);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle uploaded files callback
  const handleUploadSuccess = (newDocs) => {
    setDocuments(prev => [...newDocs, ...prev]);
    // Automatically select the newly uploaded files for querying
    const newIds = newDocs.map(d => d.id);
    setSelectedDocIds(prev => [...newIds, ...prev]);
  };

  // Toggle document selection for querying/filtering
  const handleDocSelectToggle = (docId) => {
    setSelectedDocIds(prev => {
      if (prev.includes(docId)) {
        return prev.filter(id => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  // Delete document
  const handleDeleteDocument = async (e, docId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this document? This will remove its embeddings from ChromaDB.")) return;

    try {
      await apiService.deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      setSelectedDocIds(prev => prev.filter(id => id !== docId));
      
      // Reset summary views if focused on the deleted doc
      if (focusedDocSummary && focusedDocSummary.id === docId) {
        setFocusedDocSummary(null);
      }
      setCompareSummaries(prev => prev.filter(s => s.id !== docId));
    } catch (err) {
      alert(`Error deleting document: ${err}`);
    }
  };

  // View summary dashboard of a document
  const handleViewSummary = async (doc) => {
    try {
      setActiveTab('dashboard');
      setFocusedDocSummary({
        id: doc.id,
        filename: doc.filename,
        page_count: doc.page_count,
        file_size: doc.file_size,
        loading: true
      });

      const summaryData = await apiService.getDocumentSummary(doc.id);
      setFocusedDocSummary(prev => ({
        ...prev,
        summary: summaryData.summary,
        key_findings: summaryData.key_findings,
        important_dates: summaryData.important_dates,
        loading: false
      }));
    } catch (err) {
      console.error(err);
      setFocusedDocSummary(prev => ({
        ...prev,
        summary: "Failed to load summary. Gemini API key might be missing or offline. You can try clicking 'Re-analyze Document' once configured.",
        key_findings: [],
        important_dates: [],
        loading: false
      }));
    }
  };

  // Regenerate summary for document
  const handleRegenerateSummary = async (docId) => {
    if (!focusedDocSummary) return;
    
    setFocusedDocSummary(prev => ({
      ...prev,
      loading: true
    }));
    
    try {
      const summaryData = await apiService.regenerateSummary(docId);
      setFocusedDocSummary(prev => ({
        ...prev,
        summary: summaryData.summary,
        key_findings: summaryData.key_findings,
        important_dates: summaryData.important_dates,
        loading: false
      }));
    } catch (err) {
      alert(`Failed to regenerate summary: ${err}`);
      setFocusedDocSummary(prev => ({
        ...prev,
        loading: false
      }));
    }
  };

  // Load Comparison Data for selected documents
  const handleTriggerCompare = async () => {
    if (selectedDocIds.length < 2) {
      alert("Please select at least 2 documents in the sidebar to compare them.");
      return;
    }
    
    setActiveTab('compare');
    setCompareSummaries([]);
    
    const summariesToCompare = [];
    
    for (const docId of selectedDocIds) {
      const doc = documents.find(d => d.id === docId);
      if (!doc) continue;
      
      try {
        const summaryData = await apiService.getDocumentSummary(docId);
        summariesToCompare.push({
          id: docId,
          filename: doc.filename,
          summary: summaryData.summary,
          key_findings: summaryData.key_findings,
          important_dates: summaryData.important_dates,
          page_count: doc.page_count
        });
      } catch (e) {
        summariesToCompare.push({
          id: docId,
          filename: doc.filename,
          summary: "No summary available.",
          key_findings: [],
          important_dates: [],
          page_count: doc.page_count
        });
      }
    }
    setCompareSummaries(summariesToCompare);
  };

  // Create a new session
  const handleNewSession = async () => {
    try {
      const response = await apiService.createSession(`Chat ${sessions.length + 1}`);
      setSessions(prev => [response, ...prev]);
      setCurrentSessionId(response.id);
      setMessages([]);
      setActiveTab('chat');
    } catch (err) {
      alert(`Failed to create session: ${err}`);
    }
  };

  // Select a session to load history
  const handleSelectSession = async (sessionId) => {
    setCurrentSessionId(sessionId);
    setActiveTab('chat');
    try {
      const history = await apiService.getSessionHistory(sessionId);
      setMessages(history);
    } catch (err) {
      console.error(err);
      setMessages([]);
    }
  };

  // Delete a session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation session?")) return;

    try {
      await apiService.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      if (currentSessionId === sessionId) {
        setCurrentSessionId('');
        setMessages([]);
      }
    } catch (err) {
      alert(`Failed to delete session: ${err}`);
    }
  };

  // Triggered when implicit chat session is created by sending a query
  const handleImplicitSessionCreated = (newSessionId) => {
    setCurrentSessionId(newSessionId);
    // Refresh sessions list
    apiService.listSessions().then(chatSessions => {
      setSessions(chatSessions);
    });
  };

  const formatSize = (bytes) => {
    return `${Math.round(bytes / 1024)} KB`;
  };

  return (
    <div className="flex flex-row w-full h-full overflow-hidden">
      
      {/* LEFT SIDEBAR PANEL */}
      <aside className="w-80 border-r border-slate-800/80 bg-[#090913] flex flex-col h-full shrink-0">
        
        {/* Sidebar Header / Logo */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-cyan-400 flex items-center justify-center shadow-md">
              <Sparkles size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-extrabold text-white tracking-wider glow-text-purple">
                AI DOCUMENT ANALYZER
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">Document Intelligence</p>
            </div>
          </div>
        </div>

        {/* Upload Zone Section */}
        <div className="p-4 border-b border-slate-800/60 bg-[#0b0b17]/50">
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        </div>

        {/* Scrollable File & Chat Lists */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          
          {/* Documents Checklist Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider px-1">
              <span>Indexed Documents ({documents.length})</span>
              {documents.length >= 2 && (
                <button
                  onClick={handleTriggerCompare}
                  className="text-[10px] text-violet-400 hover:text-violet-300 font-semibold flex items-center gap-0.5 border border-violet-500/25 px-1.5 py-0.5 rounded bg-violet-500/5 transition-all"
                >
                  <Layers size={10} />
                  <span>Compare</span>
                </button>
              )}
            </div>
            
            {documents.length === 0 ? (
              <div className="text-center p-4 border border-dashed border-slate-800 rounded-lg bg-slate-950/10 text-slate-500 text-[11px] leading-relaxed">
                No documents uploaded yet. Use the upload box above.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                {documents.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <div 
                      key={doc.id}
                      onClick={() => handleDocSelectToggle(doc.id)}
                      className={`flex items-center justify-between p-2 rounded-lg border text-xs cursor-pointer transition-all ${
                        isChecked 
                          ? 'bg-violet-950/10 border-violet-900/40 hover:border-violet-700/60' 
                          : 'bg-slate-950/20 border-slate-900/50 hover:bg-slate-900/10'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}} // Controlled by outer div click
                          className="rounded border-slate-800 text-violet-600 focus:ring-violet-500/40 bg-slate-950 h-3.5 w-3.5 cursor-pointer shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-slate-200 font-semibold truncate hover:text-violet-300 transition-colors" title={doc.filename}>
                            {doc.filename}
                          </p>
                          <p className="text-[9px] text-slate-500">
                            {doc.page_count} pages • {formatSize(doc.file_size)}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-1 ml-1 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewSummary(doc);
                          }}
                          title="View Summary Dashboard"
                          className="p-1 hover:bg-slate-900 text-slate-400 hover:text-violet-400 rounded transition-all"
                        >
                          <LayoutDashboard size={13} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteDocument(e, doc.id)}
                          title="Delete document"
                          className="p-1 hover:bg-slate-900 text-slate-400 hover:text-rose-400 rounded transition-all"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Chat Sessions Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider px-1">
              <span>Conversations</span>
              <button
                onClick={handleNewSession}
                className="p-1 hover:bg-slate-900 text-violet-400 hover:text-violet-300 rounded transition-all"
                title="Create New Chat"
              >
                <Plus size={14} />
              </button>
            </div>

            {sessions.length === 0 ? (
              <div 
                onClick={handleNewSession}
                className="text-center p-3 border border-dashed border-slate-800 hover:border-slate-700 rounded-lg bg-slate-950/10 hover:bg-slate-950/30 text-slate-500 text-[11px] cursor-pointer transition-all"
              >
                + Create chat session
              </div>
            ) : (
              <div className="space-y-1 max-h-[180px] overflow-y-auto pr-1">
                {sessions.map((sess) => {
                  const isActive = currentSessionId === sess.id;
                  return (
                    <div
                      key={sess.id}
                      onClick={() => handleSelectSession(sess.id)}
                      className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-all ${
                        isActive
                          ? 'bg-slate-900/80 border border-slate-700 text-white'
                          : 'bg-transparent border border-transparent text-slate-400 hover:bg-slate-900/30 hover:text-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <MessageSquare size={13} className={isActive ? 'text-violet-400' : 'text-slate-500'} />
                        <span className="truncate font-medium">{sess.title}</span>
                      </div>
                      <button
                        onClick={(e) => handleDeleteSession(e, sess.id)}
                        className="p-1 text-slate-500 hover:text-rose-400 hover:bg-slate-950/40 rounded transition-all ml-1 shrink-0"
                        title="Delete chat session"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>

      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 bg-[#05050b] flex flex-col h-full p-6 overflow-hidden">
        
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
          
          {/* Tab buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'chat'
                  ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
                  : 'bg-slate-900/60 border border-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              <MessageSquare size={14} />
              <span>Interactive Chat</span>
            </button>
            
            <button
              onClick={() => {
                if (documents.length > 0) {
                  handleViewSummary(documents[0]);
                } else {
                  alert("Please upload a document first to see summary details.");
                }
              }}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
                  : 'bg-slate-900/60 border border-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              <LayoutDashboard size={14} />
              <span>Document Summary</span>
            </button>
            
            {documents.length >= 2 && (
              <button
                onClick={handleTriggerCompare}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'compare'
                    ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/20'
                    : 'bg-slate-900/60 border border-slate-800/80 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Layers size={14} />
                <span>Doc Comparison</span>
              </button>
            )}
          </div>

          <div className="text-[11px] text-slate-500 font-semibold flex items-center gap-1 bg-slate-900/40 px-3 py-1.5 rounded-lg border border-slate-800">
            <HelpCircle size={12} className="text-violet-400" />
            <span>Select files in sidebar to narrow context search.</span>
          </div>

        </div>

        {/* Tab Content Rendering */}
        <div className="flex-1 overflow-hidden">
          
          {/* TAB 1: INTERACTIVE CHAT */}
          {activeTab === 'chat' && (
            <ChatBox
              currentSessionId={currentSessionId}
              selectedDocIds={selectedDocIds}
              documents={documents}
              messages={messages}
              setMessages={setMessages}
              onNewSessionCreated={handleImplicitSessionCreated}
              geminiStatus={backendHealth.services.gemini_api}
            />
          )}

          {/* TAB 2: DOCUMENT SUMMARY DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="h-full overflow-y-auto space-y-4 pr-1">
              {!focusedDocSummary ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 p-8 text-center border border-dashed border-slate-800/60 rounded-xl">
                  <LayoutDashboard size={40} className="text-slate-600 mb-3" />
                  <p className="text-sm font-semibold text-slate-300">No Document Selected</p>
                  <p className="text-xs text-slate-500 max-w-xs mt-1">
                    Click the dashboard icon next to an indexed document in the sidebar to review its AI analysis dashboard.
                  </p>
                </div>
              ) : focusedDocSummary.loading ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 py-20 text-center">
                  <div className="w-10 h-10 border-2 border-violet-500/25 border-t-violet-500 rounded-full animate-spin mb-4"></div>
                  <p className="text-xs font-semibold text-slate-200">Loading AI Summary Dashboard...</p>
                  <p className="text-[10px] text-slate-500 mt-1 max-w-[250px]">
                    Fetching executive summary, findings, and dates for {focusedDocSummary.filename}
                  </p>
                </div>
              ) : (
                <div className="space-y-5 animate-fade-in">
                  
                  {/* Dashboard Doc Header */}
                  <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/30 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-violet-600/10 border border-violet-500/20 text-violet-400 rounded-lg">
                        <FileText size={20} />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-100">{focusedDocSummary.filename}</h2>
                        <p className="text-[10px] text-slate-500 font-medium">
                          {focusedDocSummary.page_count} pages • {formatSize(focusedDocSummary.file_size)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <button 
                        onClick={() => handleRegenerateSummary(focusedDocSummary.id)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 font-bold border border-cyan-500/30 px-3 py-1.5 rounded-lg bg-cyan-500/5 hover:bg-cyan-500/10 transition-all"
                      >
                        Re-analyze Document
                      </button>
                      <button 
                        onClick={() => {
                          setSelectedDocIds([focusedDocSummary.id]);
                          setActiveTab('chat');
                        }}
                        className="text-xs text-violet-400 hover:text-violet-300 font-bold border border-violet-500/30 px-3 py-1.5 rounded-lg bg-violet-500/5 hover:bg-violet-500/10 transition-all"
                      >
                        Ask Question on this PDF
                      </button>
                    </div>
                  </div>

                  {/* Grid Dashboard Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    
                    {/* Card 1: Executive Summary */}
                    <div className="md:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-950/20 space-y-3 shadow-lg">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-violet-400 uppercase tracking-wider">
                        <BookOpen size={14} />
                        <span>Executive Summary</span>
                      </div>
                      <p className="text-xs md:text-sm text-slate-300 leading-relaxed font-sans font-light">
                        {focusedDocSummary.summary}
                      </p>
                    </div>

                    {/* Card 2: Key Dates */}
                    <div className="p-5 rounded-xl border border-slate-800 bg-slate-950/20 space-y-3 shadow-lg flex flex-col">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-cyan-400 uppercase tracking-wider mb-1">
                        <Calendar size={14} />
                        <span>Important Dates</span>
                      </div>
                      
                      {focusedDocSummary.important_dates && focusedDocSummary.important_dates.length > 0 ? (
                        <div className="space-y-2.5 overflow-y-auto max-h-[220px] flex-1 pr-1">
                          {focusedDocSummary.important_dates.map((dateItem, idx) => {
                            // Try to split YYYY-MM-DD from details
                            const splitIdx = dateItem.indexOf(':');
                            const dateLabel = splitIdx !== -1 ? dateItem.substring(0, splitIdx).trim() : 'Date';
                            const dateDesc = splitIdx !== -1 ? dateItem.substring(splitIdx + 1).trim() : dateItem;
                            
                            return (
                              <div key={idx} className="p-2.5 rounded-lg bg-slate-900/40 border border-slate-800/80 text-[11px] leading-relaxed">
                                <span className="font-bold text-cyan-400 block mb-0.5">{dateLabel}</span>
                                <span className="text-slate-300 font-sans">{dateDesc}</span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500 italic mt-4">No specific dates extracted.</p>
                      )}
                    </div>

                    {/* Card 3: Key Findings */}
                    <div className="md:col-span-3 p-5 rounded-xl border border-slate-800 bg-slate-950/20 space-y-3 shadow-lg">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-violet-400 uppercase tracking-wider">
                        <Layers size={14} />
                        <span>Key Findings & Highlights</span>
                      </div>
                      
                      {focusedDocSummary.key_findings && focusedDocSummary.key_findings.length > 0 ? (
                        <ul className="space-y-2">
                          {focusedDocSummary.key_findings.map((finding, idx) => (
                            <li key={idx} className="flex gap-2.5 items-start text-xs md:text-sm text-slate-300 leading-relaxed font-sans">
                              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-violet-950/40 border border-violet-500/20 text-[10px] font-bold text-violet-400 shrink-0 mt-0.5">
                                {idx + 1}
                              </span>
                              <span className="pt-0.5">{finding}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-slate-500 italic">No key findings extracted.</p>
                      )}
                    </div>

                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: DOCUMENT COMPARISON VIEW */}
          {activeTab === 'compare' && (
            <div className="h-full overflow-y-auto pr-1">
              {compareSummaries.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 py-20 text-center">
                  <div className="w-10 h-10 border-2 border-violet-500/25 border-t-violet-500 rounded-full animate-spin mb-4"></div>
                  <p className="text-xs font-semibold text-slate-200">Generating Comparison Matrix...</p>
                  <p className="text-[10px] text-slate-500 mt-1 max-w-[250px]">
                    Contrasting summaries, key findings, and dates side-by-side.
                  </p>
                </div>
              ) : (
                <div className="space-y-5 animate-fade-in">
                  
                  {/* Title Banner */}
                  <div className="p-4 rounded-xl border border-slate-800 bg-violet-950/5">
                    <h2 className="text-sm font-bold text-slate-200">Side-by-Side Document Comparison</h2>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Comparing {compareSummaries.length} selected documents across summaries, highlights, and dates.
                    </p>
                  </div>

                  {/* Grid for side-by-side comparison columns */}
                  <div className={`grid gap-4`} style={{ gridTemplateColumns: `repeat(${compareSummaries.length}, minmax(320px, 1fr))` }}>
                    
                    {compareSummaries.map((docSum) => (
                      <div key={docSum.id} className="p-5 rounded-xl border border-slate-800 bg-slate-950/20 space-y-5 flex flex-col min-w-0 shadow-lg">
                        
                        {/* Doc Metadata block */}
                        <div className="pb-3 border-b border-slate-800">
                          <h3 className="text-xs font-bold text-violet-400 truncate" title={docSum.filename}>{docSum.filename}</h3>
                          <p className="text-[9px] text-slate-500 font-medium mt-0.5">{docSum.page_count} pages</p>
                        </div>

                        {/* Executive Summary Block */}
                        <div className="space-y-2">
                          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Executive Summary</h4>
                          <p className="text-xs text-slate-300 leading-relaxed font-sans font-light">
                            {docSum.summary}
                          </p>
                        </div>

                        {/* Key Findings Block */}
                        <div className="space-y-2">
                          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Key Findings</h4>
                          {docSum.key_findings && docSum.key_findings.length > 0 ? (
                            <ul className="space-y-2">
                              {docSum.key_findings.slice(0, 4).map((finding, idx) => (
                                <li key={idx} className="flex gap-2 items-start text-[11px] text-slate-300 leading-relaxed font-sans">
                                  <span className="text-violet-400 font-bold mt-0.5">•</span>
                                  <span>{finding}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-[11px] text-slate-500 italic">No highlights extracted.</p>
                          )}
                        </div>

                        {/* Important Dates Block */}
                        <div className="space-y-2 flex-1">
                          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Important Dates</h4>
                          {docSum.important_dates && docSum.important_dates.length > 0 ? (
                            <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                              {docSum.important_dates.map((dateItem, idx) => (
                                <div key={idx} className="p-2 rounded bg-slate-900/40 border border-slate-800/80 text-[10px] leading-relaxed">
                                  <span className="font-bold text-cyan-400 block mb-0.5">{dateItem.split(':')[0]}</span>
                                  <span className="text-slate-400">{dateItem.split(':')[1] || dateItem}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-[11px] text-slate-500 italic">No dates extracted.</p>
                          )}
                        </div>

                      </div>
                    ))}

                  </div>

                </div>
              )}
            </div>
          )}

        </div>

      </main>

    </div>
  );
};

export default Home;
