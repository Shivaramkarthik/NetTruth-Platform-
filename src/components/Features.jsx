import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Server, Map, AlertTriangle, Shield, Wifi } from 'lucide-react';
import './Features.css';

const featuresData = [
  {
    title: 'Real-Time Packet Analysis',
    desc: 'Deep packet inspection algorithms to detect intentional speed drops by ISPs instantly.',
    icon: Activity,
  },
  {
    title: 'FastAPI Backend',
    desc: 'Powered by an ultra-fast Python backend to handle thousands of concurrent diagnostics.',
    icon: Server,
  },
  {
    title: 'Crowdsourced Metrics',
    desc: 'Compare your connection against thousands of users to map out throttle zones globally.',
    icon: Map,
  },
  {
    title: 'Automated Throttle Alerts',
    desc: 'Get notified via browser or native notification the second we detect bandwidth tampering.',
    icon: AlertTriangle,
  },
  {
    title: 'Data Integrity Shield',
    desc: 'End-to-end encrypted packet transmission ensuring your diagnostics remain unspoofed.',
    icon: Shield,
  },
  {
    title: 'Diagnostic Mesh',
    desc: 'Utilize peer-to-peer verification checks to accurately pinpoint network congestion points.',
    icon: Wifi,
  },
];

const Features = () => {
  return (
    <section className="features-section container" id="features">
      <motion.h2 
        className="section-title"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        Core <span style={{ color: 'var(--primary-accent)' }}>Capabilities</span>
      </motion.h2>

      <div className="features-grid">
        {featuresData.map((feature, index) => (
          <motion.div
            key={index}
            className="feature-card glass"
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
          >
            <motion.div 
              className="feature-icon-wrapper"
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ repeat: Infinity, duration: 6, ease: "linear" }}
            >
              <feature.icon />
            </motion.div>
            <h3 className="feature-title">{feature.title}</h3>
            <p className="feature-desc">{feature.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
};

export default Features;
