import React, { Suspense, lazy } from 'react';
import './App.css';
// Hero loads immediately (above the fold)
import Hero from './components/Hero';

// Everything below the fold is lazy-loaded — downloads only when needed
const NetworkMap     = lazy(() => import('./components/NetworkMap'));
const MissionStatement = lazy(() => import('./components/MissionStatement'));
const Features       = lazy(() => import('./components/Features'));
const LiveDashboard  = lazy(() => import('./components/LiveDashboard'));
const Stats          = lazy(() => import('./components/Stats'));
const Infrastructure = lazy(() => import('./components/Infrastructure'));
const DeveloperAccess = lazy(() => import('./components/DeveloperAccess'));
const Footer         = lazy(() => import('./components/Footer'));

// Lightweight placeholder shown while a section loads
const SectionFallback = () => (
  <div style={{ minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.2)', fontSize: '0.85rem', letterSpacing: '2px' }}>
    LOADING…
  </div>
);

function App() {
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
