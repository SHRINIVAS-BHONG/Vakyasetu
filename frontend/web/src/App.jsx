import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LiveBackground from './components/LiveBackground';
import InputPaper from './components/InputPaper';
import ExampleChips from './components/ExampleChips';
import ResultChapter from './components/ResultChapter';
import EmptyState from './components/EmptyState';
import ErrorState from './components/ErrorState';
import PlaceholderPage from './components/PlaceholderPage';
import AboutModal from './components/AboutModal';
import { BOOKMARK_EXAMPLES } from './config/examples';
import { MOCK_RESOLVED } from './config/mockData';

// Resolve API Base URL for Render deployment, local proxy, or custom domains
const rawApiUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE_URL = rawApiUrl && !rawApiUrl.startsWith('http://') && !rawApiUrl.startsWith('https://')
  ? `https://${rawApiUrl}`
  : rawApiUrl;

export default function App() {
  const [activeTab, setActiveTab] = useState('analyse');
  const [inputText, setInputText] = useState(BOOKMARK_EXAMPLES[0].text);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [selectedWord, setSelectedWord] = useState(null);
  const [aboutModalOpen, setAboutModalOpen] = useState(false);

  // Theme Management (Day "Paper" vs Night "Lamp")
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('vakyasetu_theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'day');
    } catch (e) {
      return 'day';
    }
  });

  // Font Scale Multiplier (A- / A+)
  const [fontScale, setFontScale] = useState(() => {
    try {
      const saved = localStorage.getItem('vakyasetu_font_scale');
      return saved ? parseFloat(saved) : 1.0;
    } catch (e) {
      return 1.0;
    }
  });

  // Calm Mode (Respects prefers-reduced-motion)
  const [calmMode, setCalmMode] = useState(() => {
    try {
      const saved = localStorage.getItem('vakyasetu_calm_mode');
      if (saved !== null) return saved === 'true';
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  });

  // Apply Theme & Font Scale to document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('vakyasetu_theme', theme);
    } catch (e) {}
  }, [theme]);

  useEffect(() => {
    document.documentElement.style.setProperty('--font-scale', fontScale.toString());
    try {
      localStorage.setItem('vakyasetu_font_scale', fontScale.toString());
    } catch (e) {}
  }, [fontScale]);

  useEffect(() => {
    if (calmMode) {
      document.body.classList.add('calm-mode');
    } else {
      document.body.classList.remove('calm-mode');
    }
    try {
      localStorage.setItem('vakyasetu_calm_mode', calmMode.toString());
    } catch (e) {}
  }, [calmMode]);

  // Initial load analysis on mount
  useEffect(() => {
    handleAnalyze(BOOKMARK_EXAMPLES[0].text);
  }, []);

  const handleToggleTheme = () => {
    setTheme(prev => prev === 'day' ? 'night' : 'day');
  };

  const handleToggleCalmMode = () => {
    setCalmMode(prev => !prev);
  };

  const handleSelectExample = (text) => {
    setInputText(text);
    handleAnalyze(text);
  };

  // Main API Fetch Logic (Preserved exact data contract)
  const handleAnalyze = async (textToAnalyze) => {
    const query = textToAnalyze !== undefined ? textToAnalyze : inputText;
    if (!query || !query.trim()) return;

    setLoading(true);
    setError(null);
    setSelectedWord(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: query.trim() }),
      });

      if (!response.ok) {
        const errDetail = await response.text();
        throw new Error(`Server returned HTTP ${response.status}: ${errDetail}`);
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      console.warn("Live API fetch notice (using verified local fallback):", err.message);
      if (!analysis) {
        setAnalysis(MOCK_RESOLVED);
      } else {
        setError(`Could not contact backend engine: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setInputText('');
    setAnalysis(null);
    setError(null);
    setSelectedWord(null);
  };

  // Switch alternative segmentation for ambiguous tokens
  const handleSelectAlternative = (surface, altWords) => {
    if (!analysis) return;
    setAnalysis(prev => {
      const nextTokens = prev.sandhi_tokens.map(tok => {
        if (tok.surface === surface) {
          return { ...tok, words: altWords };
        }
        return tok;
      });
      const allWords = nextTokens.flatMap(t => t.words);
      return {
        ...prev,
        sandhi_tokens: nextTokens,
        sandhi_splits: allWords
      };
    });
  };

  return (
    <div className="vakyasetu-app-root">
      {/* 1. Live Ambient Wallpaper Background with Scroll Parallax */}
      <LiveBackground calmMode={calmMode} />

      {/* 2. Main Paper Notebook Card */}
      <div className="notebook-stage-wrapper">
        <div className="notebook-main-paper-card">
          {/* Header & Controls */}
          <Header
            theme={theme}
            onToggleTheme={handleToggleTheme}
            fontScale={fontScale}
            onScaleChange={setFontScale}
            calmMode={calmMode}
            onToggleCalmMode={handleToggleCalmMode}
            activeTab={activeTab}
            onSelectTab={setActiveTab}
            onOpenAboutModal={() => setAboutModalOpen(true)}
          />

          {/* Tab Content Display */}
          <main className="notebook-page-viewport" id={`panel-${activeTab}`} role="tabpanel">
            {activeTab === 'analyse' ? (
              <div className="analyse-tab-flow">
                {/* 1) Hero Ruled Input */}
                <InputPaper
                  inputText={inputText}
                  setInputText={setInputText}
                  onAnalyze={handleAnalyze}
                  onClear={handleClear}
                  loading={loading}
                />

                {/* 2) Bookmark-Style Example Chips */}
                <ExampleChips
                  examples={BOOKMARK_EXAMPLES}
                  onSelectExample={handleSelectExample}
                  activeText={inputText}
                />

                {/* 3) Dynamic Analysis Result / Empty / Error States */}
                {loading && !analysis ? (
                  <EmptyState loading={true} />
                ) : error ? (
                  <ErrorState error={error} onRetry={() => handleAnalyze()} />
                ) : analysis ? (
                  <ResultChapter
                    analysis={analysis}
                    selectedWord={selectedWord}
                    onSelectWord={(w) => setSelectedWord(prev => prev === w ? null : w)}
                    onSelectAlternative={handleSelectAlternative}
                  />
                ) : (
                  <EmptyState loading={false} />
                )}
              </div>
            ) : (
              <PlaceholderPage tabId={activeTab} onOpenAboutModal={() => setAboutModalOpen(true)} />
            )}
          </main>
        </div>
      </div>

      {/* 3. About Project & Team Modal */}
      <AboutModal
        isOpen={aboutModalOpen}
        onClose={() => setAboutModalOpen(false)}
      />
    </div>
  );
}
