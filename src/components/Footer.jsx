import React from 'react';
import { Hash, MessageSquare, Camera } from 'lucide-react';
import './Footer.css';

const Footer = () => {
  return (
    <footer className="footer-section">
      <div className="container">
        <div className="footer-cta">
          <h2 className="footer-cta-headline">Take back your connection in seconds.</h2>
          <button className="btn btn-primary">Start Monitoring Free</button>
        </div>

        <div className="footer-columns">
          <div className="footer-logo-col">
            <a href="/" className="logo">NETTRUTH</a>
            <p>The definitive AI-powered platform for detecting and combating ISP bandwidth throttling.</p>
          </div>
          
          <div className="footer-col">
            <h4 className="footer-col-title">Product</h4>
            <ul className="footer-links">
              <li><a href="#">Dashboard</a></li>
              <li><a href="#">Pricing</a></li>
              <li><a href="#">Global Reports</a></li>
            </ul>
          </div>
          
          <div className="footer-col">
            <h4 className="footer-col-title">Company</h4>
            <ul className="footer-links">
              <li><a href="#">About Us</a></li>
              <li><a href="#">Mission</a></li>
              <li><a href="#">Contact</a></li>
            </ul>
          </div>
          
          <div className="footer-col">
            <h4 className="footer-col-title">Resources</h4>
            <ul className="footer-links">
              <li><a href="#">FastAPI Docs</a></li>
              <li><a href="#">Installation</a></li>
              <li><a href="#">Community Forum</a></li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="footer-copyright">
            &copy; {new Date().getFullYear()} NetTruth LLC. All rights reserved.
          </div>
          <div className="footer-socials">
            <a href="#" aria-label="Twitter"><Hash size={20}/></a>
            <a href="#" aria-label="Discord"><MessageSquare size={20}/></a>
            <a href="#" aria-label="Instagram"><Camera size={20}/></a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
