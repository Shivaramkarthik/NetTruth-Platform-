import React, { Suspense, lazy, useState, useEffect } from 'react';
import './App.css';
import Hero from './components/Hero';

// Lazy-loaded components
const NetworkMap     = lazy(() => import('./components/NetworkMap'));
const MissionStatement = lazy(() => import('./components/MissionStatement'));
const Features       = lazy(() => import('./components/Features'));
const LiveDashboard  = lazy(() => import('./components/LiveDashboard'));
const Stats          = lazy(() => import('./components/Stats'));
const Infrastructure = lazy(() => import('./components/Infrastructure'));
const DeveloperAccess = lazy(() => import('./components/DeveloperAccess'));
const Footer         = lazy(() => import('./components/Footer'));

const SectionFallback = () => (
  <div style={{ minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: '0.85rem', letterSpacing: '2px' }}>
    LOADING…
  </div>
);

function App() {
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    // Ping the backend on mount to check connectivity
    fetch('/api/v1/health')
      .then(res => {
        if (!res.ok) setBackendDown(true);
      })
      .catch(() => setBackendDown(true));
  }, []);

  return (
    <div className="app-container">
      {backendDown && (
        <div className="backend-alert">
          <span className="dot" style={{ backgroundColor: '#ff4d4d' }}></span>
          <strong>Backend Offline:</strong> The diagnostic services are currently unavailable. Please ensure the NetTruth server is running.
        </div>
      )}
      <Hero />
      <Suspense fallback={<SectionFallback />}><NetworkMap /></Suspense>
      <Suspense fallback={<SectionFallback />}><MissionStatement /></Suspense>
      <Suspense fallback={<SectionFallback />}><Features /></Suspense>
      <Suspense fallback={<SectionFallback />}><LiveDashboard /></Suspense>
      <Suspense fallback={<SectionFallback />}><Stats /></Suspense>
      <Suspense fallback={<SectionFallback />}><Infrastructure /></Suspense>
      <Suspense fallback={<SectionFallback />}><DeveloperAccess /></Suspense>
      <Suspense fallback={<SectionFallback />}><Footer /></Suspense>
    </div>
  );
}

export default App;
