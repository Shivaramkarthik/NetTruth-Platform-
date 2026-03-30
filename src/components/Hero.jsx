import React from 'react';
import { motion } from 'framer-motion';
import './Hero.css';

const Hero = () => {
  return (
    <section className="hero-section">
      <div className="hero-bg-blocks"></div>
      
      <div className="hero-content container">
        <motion.div 
          className="hero-image-container glass"
          style={{ padding: '2rem', borderRadius: '24px', border: '1px solid rgba(220, 20, 60, 0.2)' }}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        >
          <motion.video 
            src="/hero.webm" 
            autoPlay
            loop
            muted
            playsInline
            preload="none"
            className="hero-image"
            animate={{ 
              y: [0, -15, 0],
              filter: [
                'drop-shadow(0 0 20px rgba(220, 20, 60, 0.4))',
                'drop-shadow(0 0 40px rgba(220, 20, 60, 0.8))',
                'drop-shadow(0 0 20px rgba(220, 20, 60, 0.4))'
              ]
            }}
            transition={{ 
              duration: 4, 
              repeat: Infinity,
              ease: "easeInOut" 
            }}
          />
        </motion.div>

        <motion.h1 
          className="hero-title"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          NetTruth Platform
        </motion.h1>

        <motion.p 
          className="hero-subtitle"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          Uncover hidden ISP throttling. Monitor your network in real-time. Reclaim your internet speed with AI-powered diagnostics.
        </motion.p>

        <motion.div
          className="hero-actions"
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          <motion.button
            className="hero-btn-primary"
            onClick={() => document.getElementById('network-map')?.scrollIntoView({ behavior: 'smooth' })}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Start Monitoring
          </motion.button>
          <motion.a
            href="#features"
            className="hero-btn-secondary"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            Learn More
          </motion.a>
        </motion.div>

      </div>
    </section>
  );
};

export default Hero;
