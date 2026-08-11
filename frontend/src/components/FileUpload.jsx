import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertTriangle, Eye } from 'lucide-react';
import { apiService } from '../services/api';

export const FileUpload = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState('idle'); // 'idle' | 'uploading' | 'processing' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');
  const [useOcr, setUseOcr] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    validateAndUpload(files);
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    validateAndUpload(files);
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  const validateAndUpload = async (files) => {
    const pdfs = files.filter(file => file.name.toLowerCase().endsWith('.pdf'));
    
    if (pdfs.length === 0) {
      setUploadState('error');
      setErrorMsg('No PDF files detected. Please upload PDF documents only.');
      return;
    }

    setUploadState('uploading');
    setErrorMsg('');
    setUploadedFiles(pdfs.map(f => ({ name: f.name, size: f.size })));

    try {
      // Step 2: Upload to backend
      setUploadState('processing'); // Backend is running PyMuPDF, ChromaDB, and LLM summary
      const response = await apiService.uploadDocuments(pdfs, useOcr);
      
      setUploadState('success');
      if (onUploadSuccess) {
        onUploadSuccess(response);
      }
      
      // Reset back to idle after 3 seconds
      setTimeout(() => {
        setUploadState('idle');
        setUploadedFiles([]);
      }, 3000);
      
    } catch (err) {
      console.error(err);
      setUploadState('error');
      setErrorMsg(typeof err === 'string' ? err : 'Indexing failed. Check server logs.');
    }
  };

  return (
    <div className="w-full">
      {/* OCR Toggle Config */}
      <div className="flex items-center justify-between mb-3 px-1 text-xs">
        <span className="text-slate-400 font-medium">Document Settings</span>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={useOcr}
            onChange={(e) => setUseOcr(e.target.checked)}
            className="sr-only peer"
          />
          <div className="relative w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-violet-600 peer-checked:after:bg-white"></div>
          <span className="text-[11px] text-slate-400 peer-checked:text-violet-400 transition-colors">
            Enable OCR (Scanned PDFs)
          </span>
        </label>
      </div>

      {/* Upload Zone Panel */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={triggerFileInput}
        className={`w-full py-7 px-4 rounded-xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all ${
          isDragging
            ? 'border-violet-500 bg-violet-950/20 shadow-lg shadow-violet-950/20'
            : 'border-slate-800 hover:border-slate-700 bg-slate-950/20 hover:bg-slate-900/10'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          multiple
          accept=".pdf"
          className="hidden"
        />

        {uploadState === 'idle' && (
          <div className="flex flex-col items-center text-center">
            <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-full text-violet-400 mb-3 shadow-md">
              <Upload size={22} className="animate-pulse" />
            </div>
            <p className="text-xs font-semibold text-slate-200 mb-1">
              Drag & Drop PDF files here
            </p>
            <p className="text-[10px] text-slate-500">
              or click to browse from explorer
            </p>
          </div>
        )}

        {(uploadState === 'uploading' || uploadState === 'processing') && (
          <div className="flex flex-col items-center text-center">
            <div className="relative flex items-center justify-center mb-3">
              <div className="w-10 h-10 border-2 border-violet-500/20 border-t-violet-500 rounded-full animate-spin"></div>
              <FileText className="absolute text-violet-400" size={16} />
            </div>
            <p className="text-xs font-semibold text-slate-200 mb-1">
              {uploadState === 'uploading' ? 'Uploading PDF file(s)...' : 'RAG Pipeline Processing...'}
            </p>
            <div className="flex flex-col max-w-[200px] gap-0.5 mt-2">
              {uploadedFiles.map((file, idx) => (
                <span key={idx} className="text-[9px] text-violet-300 truncate font-mono">
                  {file.name} ({Math.round(file.size / 1024)} KB)
                </span>
              ))}
            </div>
            <p className="text-[9px] text-slate-500 mt-2 italic max-w-[220px]">
              {uploadState === 'processing' 
                ? 'Parsing pages, generating 384d sentence embeddings, storing in ChromaDB, and creating summary dashboard...' 
                : 'Copying file contents to uploads folder...'}
            </p>
          </div>
        )}

        {uploadState === 'success' && (
          <div className="flex flex-col items-center text-center">
            <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-full text-emerald-400 mb-3 shadow-md animate-bounce">
              <CheckCircle2 size={22} />
            </div>
            <p className="text-xs font-semibold text-emerald-400 mb-1">
              Document Indexed Successfully!
            </p>
            <p className="text-[10px] text-slate-400">
              Summaries generated and stored.
            </p>
          </div>
        )}

        {uploadState === 'error' && (
          <div className="flex flex-col items-center text-center">
            <div className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-full text-rose-400 mb-3 shadow-md">
              <AlertTriangle size={22} />
            </div>
            <p className="text-xs font-semibold text-rose-400 mb-1">
              File Indexing Failed
            </p>
            <p className="text-[10px] text-rose-300/80 max-w-[250px] leading-relaxed">
              {errorMsg}
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setUploadState('idle');
              }}
              className="mt-3 text-[10px] text-slate-400 underline hover:text-slate-200"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
