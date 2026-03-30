import React from 'react';
import { motion } from 'framer-motion';
import './Gaming.css';

const Gaming = () => {
  return (
    <section className="gaming-section">
      <div className="gaming-content container">
        <motion.h2 
          className="gaming-headline"
          initial={{ y: -30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          Level Up Your Gaming Experience
        </motion.h2>

        <motion.div 
          className="gaming-mask-container"
          initial={{ scale: 0.8, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <img 
            src="/gaming_mask.png" 
            alt="Red Mecha Mask" 
            className="gaming-mask-img pulsing-eyes" 
          />
        </motion.div>
      </div>
    </section>
  );
};

export default Gaming;
