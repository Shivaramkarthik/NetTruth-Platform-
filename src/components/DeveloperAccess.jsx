import React from 'react';
import { motion } from 'framer-motion';
import './DeveloperAccess.css';

const DeveloperAccess = () => {
  return (
    <section className="dev-section">
      <div className="dev-content container">
        <motion.h2 
          className="dev-headline"
          initial={{ y: -30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          Plug into the FastAPI Matrix
        </motion.h2>

        <motion.div 
          className="dev-image-container"
          initial={{ scale: 0.8, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <img 
            src="/nettruth_dev.png" 
            alt="API Data Terminal" 
            className="dev-image pulsing-aura" 
          />
        </motion.div>
      </div>
    </section>
  );
};

export default DeveloperAccess;
