import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import './MissionStatement.css';

const MissionStatement = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, margin: "-100px" });

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.3
      }
    }
  };

  const lineVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
  };

  return (
    <section className="mission-section" ref={ref}>
      <div className="container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <motion.div 
          className="mission-text-container"
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
        >
          <motion.span className="mission-line" variants={lineVariants}>
            NetTruth empowers users to expose
          </motion.span>
          <motion.span className="mission-line" variants={lineVariants}>
            <span className="mission-highlight">ISP throttling</span> in real-time.
          </motion.span>
          <motion.span className="mission-line" variants={lineVariants}>
            Detect limitations. Reclaim your speeds.
          </motion.span>
        </motion.div>

        {/* Glitch Transition Effect */}
        <motion.div 
          className="glitch-wrapper glitch-transition"
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 0.5 } : { opacity: 0 }}
          transition={{ delay: 1.5, duration: 1 }}
        >
          <div className="glitch-text" data-text="NETTRUTH_ONLINE">
            NETTRUTH_ONLINE
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default MissionStatement;
