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
    const apiUrl = import.meta.env.VITE_API_URL;
    if (!apiUrl) { setBackendDown(true); return; }

    const checkBackend = async (retries = 1) => {
      try {
        const res = await fetch(`${apiUrl}/ping`);
        if (res.ok) { setBackendDown(false); return; }
        throw new Error('not ok');
      } catch {
        if (retries > 0) {
          // Render free tier cold start — retry after 3s
          setTimeout(() => checkBackend(retries - 1), 3000);
        } else {
          setBackendDown(true);
        }
      }
    };
    checkBackend();
  }, []);

  return (
    <div className="app-container">

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
