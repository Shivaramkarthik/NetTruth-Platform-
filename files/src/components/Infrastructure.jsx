import React from 'react';
import { motion } from 'framer-motion';
import './Infrastructure.css';

const Infrastructure = () => {
  return (
    <section className="infra-section container">
      <motion.h2 
        className="section-title"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
      >
        Network Insights
      </motion.h2>

      <div className="infra-grid">
        <motion.div 
          className="infra-card"
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="geometric-shape shape-1"></div>
          <h3 className="infra-title">Global ISP Heatmaps</h3>
          <p className="feature-desc">Visualize real-time QoS violations and connection drops mapped dynamically worldwide.</p>
        </motion.div>

        <motion.div 
          className="infra-card"
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div className="geometric-shape shape-2"></div>
          <h3 className="infra-title">Protocol Classification</h3>
          <p className="feature-desc">Our AI accurately models which protocols (e.g. video streaming, P2P) face targeted latency traps.</p>
        </motion.div>

        <motion.div 
          className="infra-card"
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <div className="geometric-shape shape-3"></div>
          <h3 className="infra-title">Historical Forensics</h3>
          <p className="feature-desc">Archive your network's fingerprint to build an undeniable case against provider level bandwidth limiting.</p>
        </motion.div>
      </div>
    </section>
  );
};

export default Infrastructure;
