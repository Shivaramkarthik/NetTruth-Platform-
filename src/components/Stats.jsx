import React, { useEffect, useRef, useState } from 'react';
import { motion, useInView, animate } from 'framer-motion';
import { get_dashboard_summary } from '../api/nettruth';
import './Stats.css';

const Counter = ({ from, to, duration, prefix = '', suffix = '', decimals = 0 }) => {
  const nodeRef = useRef(null);
  const inView = useInView(nodeRef, { once: true, margin: '-50px' });

  useEffect(() => {
    if (inView) {
      const controls = animate(from, to, {
        duration,
        ease: 'easeOut',
        onUpdate(value) {
          if (nodeRef.current) {
            nodeRef.current.textContent = `${prefix}${value.toFixed(decimals)}${suffix}`;
          }
        },
      });
      return controls.stop;
    }
  }, [from, to, duration, inView, prefix, suffix, decimals]);

  return <span ref={nodeRef} className="stat-value">{prefix}0{suffix}</span>;
};

const Stats = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    get_dashboard_summary()
      .then(setSummary)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Live values derived from backend — fall back to demo numbers
  const download = summary?.current_speed?.download ?? 140;
  const latency  = summary?.current_speed?.latency  ?? 12;
  const delivery = summary ? Math.round((summary.speed_delivery_rate ?? 0.85) * 100) : 85;

  return (
    <section className="stats-section">
      <div className="center-asset-container">
        {/* Decorative graphic */}
      </div>

      {/* Live status badge */}
      <div style={{ textAlign: 'center', marginBottom: '2rem', position: 'relative', zIndex: 10 }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 14px',
          borderRadius: '999px',
          background: 'rgba(220,20,60,0.1)',
          border: '1px solid rgba(220,20,60,0.3)',
          fontSize: '0.75rem',
          color: '#ff4d4d',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '1px',
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: error ? '#999' : '#DC143C',
            boxShadow: error ? 'none' : '0 0 6px #DC143C',
            animation: error ? 'none' : 'pulse 1.5s infinite',
          }} />
          {loading ? 'CONNECTING...' : error ? 'OFFLINE — DEMO DATA' : 'LIVE BACKEND'}
        </span>
      </div>

      <div className="container stats-grid">
        <motion.div
          className="stat-item"
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <Counter from={0} to={download} duration={2} suffix=" Mbps" decimals={1} />
          <div className="stat-label">Live Download Speed</div>
        </motion.div>

        <motion.div
          className="stat-item"
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Counter from={0} to={delivery} duration={2.5} suffix="%" />
          <div className="stat-label">Speed Delivery Rate</div>
        </motion.div>

        <motion.div
          className="stat-item"
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Counter from={0} to={latency} duration={1.5} suffix=" ms" decimals={1} />
          <div className="stat-label">Network Latency</div>
        </motion.div>
      </div>
    </section>
  );
};

export default Stats;
