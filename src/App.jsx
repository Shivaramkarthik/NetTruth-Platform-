import React from 'react';
import './App.css';
import Hero from './components/Hero';
import NetworkMap from './components/NetworkMap';
import MissionStatement from './components/MissionStatement';
import Features from './components/Features';
import LiveDashboard from './components/LiveDashboard';
import Stats from './components/Stats';
import Infrastructure from './components/Infrastructure';
import DeveloperAccess from './components/DeveloperAccess';
import Footer from './components/Footer';

function App() {
  return (
    <div className="app-container">
      <Hero />
      <NetworkMap />
      <MissionStatement />
      <Features />
      <LiveDashboard />
      <Stats />
      <Infrastructure />
      <DeveloperAccess />
      <Footer />
    </div>
  );
}

export default App;
