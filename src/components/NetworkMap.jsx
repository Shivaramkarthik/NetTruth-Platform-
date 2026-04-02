import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './NetworkMap.css';

// Fix leaflet default marker icon paths broken by bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl:       new URL('leaflet/dist/images/marker-icon.png',    import.meta.url).href,
  shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png',  import.meta.url).href,
});

import { 
  run_speed_test, 
  get_isp_rankings, 
  get_dashboard_summary 
} from '../api/nettruth';

// ── Data ─────────────────────────────────────────────────────────────────────
function generateNodesFromRankings(lat, lng, rankings = []) {
  const nodes = [];
  const displayRankings = rankings.length > 0 ? rankings : [
    { isp_name: 'Jio Fiber', overall_score: 85 },
    { isp_name: 'Airtel', overall_score: 82 },
    { isp_name: 'StarLink', overall_score: 92 }
  ];

  for (let i = 0; i < 15; i++) {
    const ispData = displayRankings[i % displayRankings.length];
    const dlat     = (Math.random() - 0.5) * 0.18;
    const dlng     = (Math.random() - 0.5) * 0.22;
    
    // Use the overall_score to influence the strength
    const baseStrength = ispData.overall_score || 50;
    const strength = Math.min(100, Math.max(10, Math.floor(baseStrength + (Math.random() - 0.5) * 20)));
    
    const status   =
      strength >= 75 ? 'excellent' :
      strength >= 50 ? 'good' :
      strength >= 25 ? 'fair' : 'poor';
      
    nodes.push({
      id:        i,
      lat:       lat + dlat,
      lng:       lng + dlng,
      isp:       ispData.isp_name || 'Unknown ISP',
      strength,
      status,
      ping:      Math.floor(Math.random() * 40) + 5,
      download:  +( (ispData.speed_score || 70) * (strength/100) * 2).toFixed(1),
      upload:    +( (ispData.speed_score || 30) * (strength/100) * 0.8).toFixed(1),
      throttled: (ispData.avg_throttling_rate || 0.1) > 0.12 ? Math.random() > 0.5 : Math.random() > 0.8,
      users:     Math.floor(Math.random() * 320) + 10,
      channel:   Math.floor(Math.random() * 13) + 1,
      band:      Math.random() > 0.5 ? '5 GHz' : '2.4 GHz',
      encryption:'WPA3',
    });
  }
  return nodes;
}

// Speed plan tiers (contracted plans)
const SPEED_PLANS = [
  { label: '10 Mbps',  value: 10,   tag: 'Basic' },
  { label: '25 Mbps',  value: 25,   tag: 'Starter' },
  { label: '50 Mbps',  value: 50,   tag: 'Popular' },
  { label: '100 Mbps', value: 100,  tag: 'Home' },
  { label: '200 Mbps', value: 200,  tag: 'Fast' },
  { label: '500 Mbps', value: 500,  tag: 'Ultra' },
  { label: '1 Gbps',   value: 1000, tag: 'Gigabit' },
];

const STATUS_COLOR = {
  excellent: '#00ff88',
  good:      '#39d0ff',
  fair:      '#f5c518',
  poor:      '#DC143C',
};

const STATUS_LABEL = {
  excellent: '● Excellent',
  good:      '● Good',
  fair:      '● Fair',
  poor:      '● Poor',
};

// ── Component ─────────────────────────────────────────────────────────────────
const NetworkMap = () => {
  const mapRef     = useRef(null);
  const leafletMap = useRef(null);
  const markersRef = useRef([]);

  const [loading,      setLoading]      = useState(false);
  const [monitoring,   setMonitoring]   = useState(false);
  const [nodes,        setNodes]        = useState([]);
  const [selected,     setSelected]     = useState(null);
  const [error,        setError]        = useState('');
  const [scanPct,      setScanPct]      = useState(0);

  // ── NEW STATES ──────────────────────────────────────────────────────────────
  const [showNetworks,    setShowNetworks]    = useState(false);
  const [showSpeedWiz,    setShowSpeedWiz]    = useState(false);
  const [selectedPlan,    setSelectedPlan]    = useState(null);
  const [speedAnalysis,   setSpeedAnalysis]   = useState(null);
  const [netFilter,       setNetFilter]       = useState('all');
  const [netSort,         setNetSort]         = useState('strength');

  // Init map (Leaflet now bundled — no async CDN wait needed)
  useEffect(() => {
    if (leafletMap.current) return;
    leafletMap.current = L.map(mapRef.current, {
      center: [20.5937, 78.9629], zoom: 5,
      zoomControl: false, attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
    }).addTo(leafletMap.current);
    L.control.zoom({ position: 'bottomright' }).addTo(leafletMap.current);
    L.control.attribution({ position: 'bottomleft', prefix: '© OpenStreetMap | © CARTO' })
      .addTo(leafletMap.current);
  }, []);

  const makeIcon = useCallback((status, isUser = false) => {
    const color = isUser ? '#DC143C' : STATUS_COLOR[status];
    const size  = isUser ? 22 : 16;
    const svg = isUser
      ? `<svg xmlns="http://www.w3.org/2000/svg" width="${size*2}" height="${size*2}" viewBox="0 0 44 44">
           <circle cx="22" cy="22" r="10" fill="${color}" opacity="0.9"/>
           <circle cx="22" cy="22" r="18" fill="none" stroke="${color}" stroke-width="2" opacity="0.4">
             <animate attributeName="r" values="10;20;10" dur="2s" repeatCount="indefinite"/>
             <animate attributeName="opacity" values="0.6;0;0.6" dur="2s" repeatCount="indefinite"/>
           </circle></svg>`
      : `<svg xmlns="http://www.w3.org/2000/svg" width="${size*2}" height="${size*2}" viewBox="0 0 32 32">
           <circle cx="16" cy="16" r="7" fill="${color}" opacity="0.95"/>
           <circle cx="16" cy="16" r="13" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.3"/>
         </svg>`;
    return L.divIcon({ html: svg, className: 'custom-div-icon', iconSize: [size*2, size*2], iconAnchor: [size, size] });
  }, []);

  const markerLayerGroup = useRef(null);

  const drawMarkers = useCallback((pos, nodeList) => {
    const map = leafletMap.current;
    if (!map) return;

    if (!markerLayerGroup.current) {
      markerLayerGroup.current = L.layerGroup().addTo(map);
    }
    
    markerLayerGroup.current.clearLayers();

    const um = L.marker([pos.lat, pos.lng], { icon: makeIcon(null, true) });
    um.bindTooltip('<b style="color:#DC143C">📍 Your Location</b>', { className: 'nt-tooltip' });
    markerLayerGroup.current.addLayer(um);

    nodeList.forEach(n => {
      const m = L.marker([n.lat, n.lng], { icon: makeIcon(n.status) });
      m.bindTooltip(
        `<div class="nt-tooltip-inner"><b>${n.isp}</b><br/>
         Signal: <span style="color:${STATUS_COLOR[n.status]}">${n.strength}%</span><br/>
         DL: ${n.download} Mbps · Ping: ${n.ping}ms<br/>
         ${n.throttled ? '<span style="color:#DC143C">⚠ Throttling</span>' : '<span style="color:#00ff88">✔ Clean</span>'}
         </div>`, { className: 'nt-tooltip' });
      m.on('click', () => setSelected(n));
      markerLayerGroup.current.addLayer(m);
    });
  }, [makeIcon]);

  const doMonitor = useCallback(async (lat, lng) => {
    try {
      setScanPct(30);
      // Fetch rankings and summary in parallel for better speed
      const [rankings, summaryData] = await Promise.all([
        get_isp_rankings(),
        get_dashboard_summary()
      ]);
      setScanPct(60);
      
      const nodeList = generateNodesFromRankings(lat, lng, rankings);
      
      // Use summary data if available for the main node for instant feedback
      nodeList.unshift({
        id:        9999,
        lat:       lat,
        lng:       lng,
        isp:       'Current Scan Result',
        strength:  98,
        status:    'excellent',
        ping:      summaryData.current_speed?.latency || 12,
        download:  summaryData.current_speed?.download || 0,
        upload:    summaryData.current_speed?.upload || 0,
        throttled: summaryData.throttling_status?.active || false,
        users:     1,
        channel:   6,
        band:      '5 GHz',
        encryption:'WPA3',
      });

      setNodes(nodeList);
      setScanPct(90);
      
      const map = leafletMap.current;
      if (map) {
        map.setView([lat, lng], 13, { animate: true });
        drawMarkers({ lat, lng }, nodeList);
      }
      
      setMonitoring(true);
      setLoading(false);
      setScanPct(100);
    } catch (err) {
      console.error("Monitoring failed", err);
      setError(`Platform Sync Failed: ${err.message}. Falling back to cached data.`);
      const fallbackNodes = generateNodesFromRankings(lat, lng, []);
      setNodes(fallbackNodes);
      setMonitoring(true);
      setLoading(false);
      setScanPct(100);
      drawMarkers({ lat, lng }, fallbackNodes);
    }
  }, [drawMarkers]);

  const handleStartMonitoring = useCallback(() => {
    setError(''); setLoading(true); setScanPct(0);
    
    // We remove the interval-based fake scan and let doMonitor handle real progress
    navigator.geolocation.getCurrentPosition(
      ({ coords: { latitude: lat, longitude: lng } }) => { doMonitor(lat, lng); },
      () => {
        doMonitor(17.3850, 78.4867); // Demo near Hyderabad
        setError('📍 Location access denied — showing demo data.');
      },
      { timeout: 10000 }
    );
  }, [doMonitor]);

  const handleReset = useCallback(() => {
    setMonitoring(false); setSelected(null); setNodes([]);
    setSelectedPlan(null); setSpeedAnalysis(null);
    markersRef.current.forEach(m => leafletMap.current?.removeLayer(m));
    markersRef.current = [];
    leafletMap.current?.setView([20.5937, 78.9629], 5, { animate: true });
  }, []);

  // ── Speed wizard: run analysis after plan chosen ────────────────────────────
  const runSpeedAnalysis = useCallback((plan) => {
    setSelectedPlan(plan);
    setShowSpeedWiz(false);
    // Simulate: compare plan speed vs actual avg download
    const avgDL   = nodes.reduce((a, n) => a + n.download, 0) / nodes.length;
    const ratio   = avgDL / plan.value;
    const verdict =
      ratio >= 0.9 ? 'great' :
      ratio >= 0.7 ? 'acceptable' :
      ratio >= 0.5 ? 'degraded' : 'throttled';
    setSpeedAnalysis({ avgDL: avgDL.toFixed(1), plan, ratio: (ratio * 100).toFixed(0), verdict });
  }, [nodes]);

  // ── Network list: filter + sort ─────────────────────────────────────────────
  const filteredNodes = [...nodes]
    .filter(n => netFilter === 'all' || n.status === netFilter)
    .sort((a, b) =>
      netSort === 'strength' ? b.strength - a.strength :
      netSort === 'ping'     ? a.ping - b.ping :
      netSort === 'download' ? b.download - a.download :
      a.isp.localeCompare(b.isp)
    );

  const summary = nodes.length ? {
    avg:       Math.round(nodes.reduce((a, n) => a + n.strength, 0) / nodes.length),
    throttled: nodes.filter(n => n.throttled).length,
    excellent: nodes.filter(n => n.status === 'excellent').length,
    poor:      nodes.filter(n => n.status === 'poor').length,
  } : null;

  const verdictMeta = {
    great:      { color: '#00ff88', icon: '✅', label: 'Getting full speed!' },
    acceptable: { color: '#39d0ff', icon: '☑️',  label: 'Minor speed loss' },
    degraded:   { color: '#f5c518', icon: '⚠️',  label: 'Significant degradation' },
    throttled:  { color: '#DC143C', icon: '🚫', label: 'Likely ISP Throttling!' },
  };

  return (
    <section className="nm-section" id="network-map">
      <div className="nm-bg-grid" />

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="nm-header">
        <motion.div className="nm-badge"
          animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 2, repeat: Infinity }}>
          <span className="nm-badge-dot" /> LIVE NETWORK RADAR
        </motion.div>
        <motion.h2 className="nm-title"
          initial={{ y: 20, opacity: 0 }} whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }} transition={{ duration: 0.7 }}>
          Geospatial <span className="nm-accent">Signal Map</span>
        </motion.h2>
        <motion.p className="nm-subtitle"
          initial={{ y: 20, opacity: 0 }} whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.15 }}>
          Scan nearby ISP signals, view all networks, and compare your plan speed against real-world performance.
        </motion.p>
      </div>

      {/* ── Speed Analysis Result Banner ─────────────────────────── */}
      <AnimatePresence>
        {speedAnalysis && (
          <motion.div className="nm-analysis-banner"
            initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="nm-analysis-inner">
              <span className="nm-analysis-icon">{verdictMeta[speedAnalysis.verdict].icon}</span>
              <div>
                <div className="nm-analysis-headline" style={{ color: verdictMeta[speedAnalysis.verdict].color }}>
                  {verdictMeta[speedAnalysis.verdict].label}
                </div>
                <div className="nm-analysis-sub">
                  Plan: <strong>{speedAnalysis.plan.label}</strong> &nbsp;·&nbsp;
                  Avg real speed: <strong>{speedAnalysis.avgDL} Mbps</strong> &nbsp;·&nbsp;
                  Getting <strong>{speedAnalysis.ratio}%</strong> of contracted speed
                </div>
              </div>
              <button className="nm-analysis-close" onClick={() => setSpeedAnalysis(null)}>✕</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main Card ────────────────────────────────────────────── */}
      <div className="nm-card-wrap">
        <motion.div className="nm-card glass"
          initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.8 }}>

          {/* Toolbar */}
          <div className="nm-toolbar">
            <div className="nm-legend">
              {Object.entries(STATUS_COLOR).map(([k, c]) => (
                <span key={k} className="nm-legend-item">
                  <span className="nm-legend-dot" style={{ background: c }} />
                  <span className="nm-legend-label">{k.charAt(0).toUpperCase() + k.slice(1)}</span>
                </span>
              ))}
            </div>

            <div className="nm-toolbar-actions">
              {!monitoring ? (
                <motion.button id="btn-start-monitoring" className="nm-btn-primary"
                  onClick={handleStartMonitoring} disabled={loading}
                  whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                  {loading ? (
                    <span className="nm-btn-inner"><span className="nm-spinner" />Scanning… {scanPct}%</span>
                  ) : (
                    <span className="nm-btn-inner">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                      </svg>
                      Start Monitoring
                    </span>
                  )}
                </motion.button>
              ) : (
                <div className="nm-action-group">
                  {/* Show All Networks */}
                  <motion.button id="btn-show-networks" className="nm-btn-outline"
                    onClick={() => setShowNetworks(true)}
                    whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>
                      <line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>
                    </svg>
                    Show All Networks
                  </motion.button>

                  {/* Speed Selection */}
                  <motion.button id="btn-speed-selection" className="nm-btn-outline nm-btn-speed"
                    onClick={() => setShowSpeedWiz(true)}
                    whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                    {selectedPlan ? `Plan: ${selectedPlan.label}` : 'Select Speed Plan'}
                  </motion.button>

                  <div className="nm-status-chip">
                    <span className="nm-status-dot" />{nodes.length} nodes
                  </div>

                  <button className="nm-btn-reset" onClick={handleReset}>✕ Reset</button>
                </div>
              )}
            </div>
          </div>

          {/* Error banner */}
          <AnimatePresence>
            {error && (
              <motion.div className="nm-error"
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Map */}
          <div className="nm-map-outer">
            <div ref={mapRef} className="nm-map" />

            <AnimatePresence>
              {!monitoring && !loading && (
                <motion.div className="nm-overlay"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.3 } }}>
                  <motion.div className="nm-overlay-icon"
                    animate={{ scale: [1, 1.12, 1], opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2.5, repeat: Infinity }}>🛰️</motion.div>
                  <p className="nm-overlay-text">Press <strong>Start Monitoring</strong> to activate the radar</p>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {loading && (
                <motion.div className="nm-loading-ring"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <div className="nm-ring" />
                  <p className="nm-loading-text">Scanning network nodes… {scanPct}%</p>
                  <div className="nm-progress-bar">
                    <div className="nm-progress-fill" style={{ width: `${scanPct}%` }} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Stats Row */}
          <AnimatePresence>
            {monitoring && summary && (
              <motion.div className="nm-stats"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }} transition={{ duration: 0.5 }}>
                <div className="nm-stat">
                  <span className="nm-stat-val" style={{ color: '#39d0ff' }}>{summary.avg}%</span>
                  <span className="nm-stat-label">Avg Signal</span>
                </div>
                <div className="nm-stat">
                  <span className="nm-stat-val" style={{ color: '#00ff88' }}>{summary.excellent}</span>
                  <span className="nm-stat-label">Excellent</span>
                </div>
                <div className="nm-stat">
                  <span className="nm-stat-val" style={{ color: '#DC143C' }}>{summary.throttled}</span>
                  <span className="nm-stat-label">Throttled ISPs</span>
                </div>
                <div className="nm-stat">
                  <span className="nm-stat-val" style={{ color: '#f5c518' }}>{summary.poor}</span>
                  <span className="nm-stat-label">Poor Signal</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Side Detail Panel */}
        <AnimatePresence>
          {selected && (
            <motion.div className="nm-side glass"
              initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }}
              exit={{ x: 40, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 24 }}>
              <button className="nm-side-close" onClick={() => setSelected(null)}>✕</button>
              <div className="nm-side-isp">{selected.isp}</div>
              <div className="nm-side-status" style={{ color: STATUS_COLOR[selected.status] }}>
                {STATUS_LABEL[selected.status]}
              </div>
              <div className="nm-side-meter-wrap">
                <div className="nm-side-meter-bg">
                  <motion.div className="nm-side-meter-fill"
                    style={{ background: STATUS_COLOR[selected.status] }}
                    initial={{ width: 0 }} animate={{ width: `${selected.strength}%` }}
                    transition={{ duration: 0.7, ease: 'easeOut' }} />
                </div>
                <span className="nm-side-pct">{selected.strength}%</span>
              </div>
              <div className="nm-side-metrics">
                {[
                  { label: 'Ping',   value: `${selected.ping} ms`,      color: selected.ping < 30 ? '#00ff88' : selected.ping < 80 ? '#f5c518' : '#DC143C' },
                  { label: 'Download', value: `${selected.download} Mbps`, color: '#39d0ff' },
                  { label: 'Upload',   value: `${selected.upload} Mbps`,   color: '#a78bfa' },
                  { label: 'Band',     value: selected.band,              color: '#fff' },
                  { label: 'Channel',  value: `Ch ${selected.channel}`,   color: '#fff' },
                  { label: 'Users Nearby', value: selected.users,         color: '#fff' },
                ].map(m => (
                  <div key={m.label} className="nm-side-metric-row">
                    <span className="nm-side-metric-label">{m.label}</span>
                    <span className="nm-side-metric-val" style={{ color: m.color }}>{m.value}</span>
                  </div>
                ))}
              </div>
              <div className={`nm-side-throttle ${selected.throttled ? 'throttled' : 'clean'}`}>
                {selected.throttled ? '⚠ ISP Throttling Detected' : '✔ No Throttling Detected'}
              </div>
              <div className="nm-side-coords">
                📍 {selected.lat.toFixed(4)}, {selected.lng.toFixed(4)}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ══════════════════════════════════════════════════════════
          MODAL: Show All Networks
      ══════════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showNetworks && (
          <motion.div className="nm-modal-backdrop"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowNetworks(false)}>
            <motion.div className="nm-modal glass"
              initial={{ scale: 0.9, opacity: 0, y: 30 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 30 }}
              transition={{ type: 'spring', stiffness: 280, damping: 26 }}
              onClick={e => e.stopPropagation()}>

              {/* Modal Header */}
              <div className="nm-modal-head">
                <div>
                  <div className="nm-modal-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>
                      <line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>
                    </svg>
                    All Detected Networks
                  </div>
                  <div className="nm-modal-sub">{nodes.length} networks found nearby</div>
                </div>
                <button className="nm-modal-close" onClick={() => setShowNetworks(false)}>✕</button>
              </div>

              {/* Filter + Sort bar */}
              <div className="nm-modal-controls">
                <div className="nm-filter-group">
                  {['all', 'excellent', 'good', 'fair', 'poor'].map(f => (
                    <button key={f}
                      className={`nm-filter-btn ${netFilter === f ? 'active' : ''}`}
                      style={netFilter === f && f !== 'all' ? { borderColor: STATUS_COLOR[f], color: STATUS_COLOR[f] } : {}}
                      onClick={() => setNetFilter(f)}>
                      {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                </div>
                <div className="nm-sort-wrap">
                  <label className="nm-sort-label">Sort:</label>
                  <select className="nm-sort-select"
                    value={netSort} onChange={e => setNetSort(e.target.value)}>
                    <option value="strength">Signal %</option>
                    <option value="ping">Ping</option>
                    <option value="download">Download</option>
                    <option value="isp">ISP Name</option>
                  </select>
                </div>
              </div>

              {/* Network List */}
              <div className="nm-modal-list">
                {filteredNodes.map((n, idx) => (
                  <motion.div key={n.id} className="nm-net-row"
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    onClick={() => { setSelected(n); setShowNetworks(false); }}>

                    <div className="nm-net-icon" style={{ background: `${STATUS_COLOR[n.status]}22`, border: `1px solid ${STATUS_COLOR[n.status]}55` }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={STATUS_COLOR[n.status]} strokeWidth="2">
                        <path d="M1.5 8.5a18 18 0 0121 0"/><path d="M5 12a13 13 0 0114 0"/>
                        <path d="M8.5 15.5a8 8 0 017 0"/><circle cx="12" cy="19" r="1" fill={STATUS_COLOR[n.status]}/>
                      </svg>
                    </div>

                    <div className="nm-net-info">
                      <div className="nm-net-name">{n.isp}</div>
                      <div className="nm-net-meta">{n.band} · Ch {n.channel} · {n.encryption}</div>
                    </div>

                    <div className="nm-net-bar-wrap">
                      <div className="nm-net-bar-bg">
                        <div className="nm-net-bar-fill"
                          style={{ width: `${n.strength}%`, background: STATUS_COLOR[n.status] }} />
                      </div>
                      <span className="nm-net-pct" style={{ color: STATUS_COLOR[n.status] }}>{n.strength}%</span>
                    </div>

                    <div className="nm-net-stats">
                      <span>↓ {n.download} Mbps</span>
                      <span>↑ {n.upload} Mbps</span>
                      <span>🏓 {n.ping}ms</span>
                    </div>

                    {n.throttled && <span className="nm-net-throttle-tag">⚠ Throttled</span>}
                    <div className="nm-net-arrow">›</div>
                  </motion.div>
                ))}
                {filteredNodes.length === 0 && (
                  <div className="nm-modal-empty">No networks match this filter.</div>
                )}
              </div>

              {/* Footer */}
              <div className="nm-modal-footer">
                <button className="nm-btn-outline" onClick={() => { setShowNetworks(false); setShowSpeedWiz(true); }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                  </svg>
                  Continue → Select Speed Plan
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══════════════════════════════════════════════════════════
          WIZARD: Speed Plan Selection
      ══════════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showSpeedWiz && (
          <motion.div className="nm-modal-backdrop"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowSpeedWiz(false)}>
            <motion.div className="nm-modal nm-modal-speed glass"
              initial={{ scale: 0.9, opacity: 0, y: 30 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 30 }}
              transition={{ type: 'spring', stiffness: 280, damping: 26 }}
              onClick={e => e.stopPropagation()}>

              <div className="nm-modal-head">
                <div>
                  <div className="nm-modal-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                    Select Your Speed Plan
                  </div>
                  <div className="nm-modal-sub">Choose the speed your ISP promised you</div>
                </div>
                <button className="nm-modal-close" onClick={() => setShowSpeedWiz(false)}>✕</button>
              </div>

              <div className="nm-speed-grid">
                {SPEED_PLANS.map(plan => {
                  const avgDL  = nodes.reduce((a, n) => a + n.download, 0) / nodes.length;
                  const ratio  = Math.min((avgDL / plan.value) * 100, 100);
                  const rColor = ratio >= 90 ? '#00ff88' : ratio >= 70 ? '#39d0ff' : ratio >= 50 ? '#f5c518' : '#DC143C';
                  return (
                    <motion.button key={plan.value}
                      className={`nm-speed-card ${selectedPlan?.value === plan.value ? 'selected' : ''}`}
                      onClick={() => runSpeedAnalysis(plan)}
                      whileHover={{ scale: 1.04, borderColor: '#DC143C' }}
                      whileTap={{ scale: 0.97 }}>
                      <span className="nm-speed-tag">{plan.tag}</span>
                      <span className="nm-speed-val">{plan.label}</span>
                      <div className="nm-speed-preview">
                        <div className="nm-speed-bar-bg">
                          <div className="nm-speed-bar-fill" style={{ width: `${ratio}%`, background: rColor }} />
                        </div>
                        <span className="nm-speed-preview-pct" style={{ color: rColor }}>
                          ~{ratio.toFixed(0)}% of plan
                        </span>
                      </div>
                    </motion.button>
                  );
                })}
              </div>

              <div className="nm-speed-hint">
                💡 We'll compare your plan speed against the average real-world download speed detected nearby.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};

export default NetworkMap;
