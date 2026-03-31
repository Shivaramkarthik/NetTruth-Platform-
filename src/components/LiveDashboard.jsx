import React, { useEffect, useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  run_speed_test,
  analyze_throttling,
  get_quick_check,
  predict_throttling,
  get_dashboard_summary,
  get_isp_rating,
  get_isp_rankings,
  get_network_logs,
  generate_report,
} from '../api/nettruth';
import './LiveDashboard.css';

// ── Helpers ───────────────────────────────────────────────────────────────────
const Spinner = () => <span className="spinner" />;

const PanelHeader = ({ title, endpoint, live = false }) => (
  <div className="panel-header">
    <div>
      <div className="panel-title">
        {live && <span className="dot" />}
        {title}
      </div>
      <div className="panel-endpoint">{endpoint}</div>
    </div>
  </div>
);

// Custom hook for polling
function useInterval(callback, delay) {
  const savedCallback = useRef();
  useEffect(() => { savedCallback.current = callback; }, [callback]);
  useEffect(() => {
    function tick() { savedCallback.current(); }
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}

// ── 1. run_speed_test — POST /api/v1/speed-test ─────────────────────
const RunSpeedTestPanel = () => {
  const [data, setData] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  
  const [displayVals, setDisplayVals] = useState({ dl: 0, ul: 0, ping: 0 });

  const runSpeedTest = async () => {
    setIsBusy(true);
    setStatusMsg('Preparing measurements...');
    
    // Reset display
    document.getElementById("download").innerText = "0";
    document.getElementById("upload").innerText = "0";
    document.getElementById("latency").innerText = "0";

    try {
      // 1. Latency Measurement (Ping)
      setStatusMsg('Measuring latency...');
      const t0 = performance.now();
      await fetch('/api/v1/health', { cache: 'no-store' });
      const pingVal = (performance.now() - t0).toFixed(2);
      document.getElementById("latency").innerText = pingVal;

      // 2. Download Speed (Mbps) - 10MB test file
      setStatusMsg('Measuring download speed...');
      const dlUrl = "https://cachefly.cachefly.net/10mb.test?cb=" + Date.now();
      const t1 = performance.now();
      const dlResp = await fetch(dlUrl, { cache: 'no-store' });
      const dlBlob = await dlResp.blob();
      const t2 = performance.now();
      const dlMbps = ((dlBlob.size * 8) / ((t2 - t1) / 1000) / (1024 * 1024)).toFixed(2);
      document.getElementById("download").innerText = dlMbps;

      // 3. Upload Speed (Mbps) - 1MB Blob
      setStatusMsg('Measuring upload speed...');
      const ulSize = 1024 * 1024 * 1; // 1MB
      const ulBlob = new Blob([new Uint8Array(ulSize)]);
      const t3 = performance.now();
      await fetch('https://httpbin.org/post', {
        method: 'POST',
        body: ulBlob,
        cache: 'no-store'
      });
      const t4 = performance.now();
      const ulMbps = ((ulSize * 8) / ((t4 - t3) / 1000) / (1024 * 1024)).toFixed(2);
      document.getElementById("upload").innerText = ulMbps;

      setStatusMsg('Test successful.');
    } catch (err) {
      console.error(err);
      setError("Network test failed. Please try again.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleClick = useCallback(() => {
    runSpeedTest();
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="Run Speed Test" endpoint="Real-time network speed measurement" live />
      <button id="run-speed-test" className="api-btn api-btn-primary" onClick={handleClick} disabled={isBusy}>
        {isBusy ? <><Spinner /> Testing…</> : '▶ Run Speed Test'}
      </button>
      {isBusy && <p className="status-message">{statusMsg}</p>}
      {error && <p className="panel-error">⚠ {error}</p>}
      {(data || isBusy || (displayVals.dl === 0 && displayVals.ul === 0)) && (
        <motion.div className="speed-cards" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="speed-card">
            <div id="download" className="speed-card-val">{displayVals.dl}</div>
            <div className="speed-card-label">download_speed (Mbps)</div>
          </div>
          <div className="speed-card">
            <div id="upload" className="speed-card-val">{displayVals.ul}</div>
            <div className="speed-card-label">upload_speed (Mbps)</div>
          </div>
          <div className="speed-card">
            <div id="latency" className="speed-card-val">{displayVals.ping}</div>
            <div className="speed-card-label">latency (ms)</div>
          </div>
        </motion.div>
      )}
      {data?.server && !isBusy && (
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '10px' }}>
          Test Server: <strong style={{ color: 'var(--text-primary)' }}>{data.server}</strong>
        </div>
      )}
    </div>
  );
};

// ── 2. analyze_throttling — POST /api/v1/analyze-throttling ─────────────────
const AnalyzeThrottlingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await analyze_throttling()); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="Analyze Throttling" endpoint="AI-powered traffic pattern analysis" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Analysing…</> : '⚡ Analyze Throttling'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row">
            <span className="result-key">throttling_detected</span>
            <span className={`result-val ${data?.throttling_detected ? 'danger' : 'safe'}`}>
              {String(data?.throttling_detected || false)}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">type</span>
            <span className="result-val">{data?.type || "N/A"}</span>
          </div>
          <div className="result-row">
            <span className="result-key">severity</span>
            <span className={`result-val ${data?.severity === 'high' ? 'danger' : data?.severity === 'medium' ? 'warn' : ''}`}>
              {data?.severity || "N/A"}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">affected_services</span>
            <span className="result-val" style={{ fontSize: '0.75rem' }}>
              {data?.affected_services?.length ? data.affected_services.join(', ') : '—'}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">recommendation</span>
            <span className="result-val" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', maxWidth: '55%', textAlign: 'right' }}>
              {data?.recommendation || "N/A"}
            </span>
          </div>
          <div className="conf-bar-wrap">
            <div className="conf-bar-fill" style={{ width: `${Math.round((data?.confidence || 0) * 100)}%` }} />
          </div>
          <p style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
            confidence: {Math.round((data?.confidence || 0) * 100)}%
          </p>
        </motion.div>
      )}
    </div>
  );
};

// ── 3. get_quick_check — GET /api/v1/quick-check ─────────────────
const GetQuickCheckPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState(true);

  const fetchCheck = useCallback(async () => {
    if (loading) return; 
    setLoading(true);
    try { 
      const res = await get_quick_check(); 
      setData(res);
      setBackendOnline(true);
    } catch (e) { 
      setBackendOnline(false); 
    } finally { 
      setLoading(false); 
    }
  }, [loading]);

  // Real-time polling specifically isolated to Quick Check
  useInterval(() => { fetchCheck(); }, 5000); 

  return (
    <div className="dashboard-panel">
      <PanelHeader title="Quick Check" endpoint="Instant status verification" live />
      <button className="api-btn api-btn-outline" onClick={fetchCheck} disabled={loading}>
        {loading ? <><Spinner /> Checking…</> : '🔍 Quick Check'}
      </button>
      
      {!backendOnline && <p className="panel-error">⚠ Backend Offline</p>}
      
      {backendOnline && data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row">
            <span className="result-key">status</span>
            <span className={`result-val ${data?.status === 'good' ? 'safe' : data?.status === 'moderate' ? 'warn' : 'danger'}`}>
              {data?.status || 'N/A'}
            </span>
          </div>
          {/* Removed avg_speed per instructions */}
          <div className="result-row">
            <span className="result-key">latency (ms)</span>
            <span className="result-val">{data?.latency || 0}</span>
          </div>
          <div className="result-row">
            <span className="result-key">latency_classification</span>
            <span className={`result-val ${data?.latency_classification === 'Excellent' || data?.latency_classification === 'Good' ? 'safe' : data?.latency_classification === 'Moderate' ? 'warn' : 'danger'}`}>
              {data?.latency_classification || 'N/A'}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">analysis.explanation</span>
            <span className="result-val" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {data?.analysis?.explanation || "No explanation provided."}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
};

// ── 4. get_dashboard_summary — GET /api/v1/dashboard/summary ────────────────
const GetDashboardSummaryPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if(loading) return;
    setLoading(true);
    try { setData(await get_dashboard_summary()); setError(null); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, [loading]);

  // Poll every 10 seconds for real-time dashboard updates
  useInterval(() => { fetchData(); }, 10000);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="Dashboard Summary" endpoint="Current network health overview" live />
      <button className="api-btn api-btn-outline" onClick={fetchData} disabled={loading}>
        {loading ? <><Spinner /> Loading…</> : '📊 Dashboard Summary'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row"><span className="result-key">network_health</span><span className={`result-val ${data?.network_health === 'Good' ? 'safe' : 'danger'}`}>{data?.network_health || 'N/A'}</span></div>
          <div className="result-row"><span className="result-key">current_speed.download</span><span className="result-val">{data?.current_speed?.download || 0} Mbps</span></div>
          <div className="result-row"><span className="result-key">current_speed.latency</span><span className="result-val">{data?.current_speed?.latency || 0} ms</span></div>
          <div className="result-row"><span className="result-key">promised_speed</span><span className="result-val">{data?.promised_speed || 0} Mbps</span></div>
          <div className="result-row"><span className="result-key">speed_delivery_rate</span><span className={`result-val ${(data?.speed_delivery_rate || 0) < 0.7 ? 'danger' : 'safe'}`}>{Math.round((data?.speed_delivery_rate || 0) * 100)}%</span></div>
          <div className="result-row"><span className="result-key">throttling_status.active</span><span className={`result-val ${data?.throttling_status?.active ? 'danger' : 'safe'}`}>{String(data?.throttling_status?.active || false)}</span></div>
          {data?.alerts?.length > 0 && (
            <div className="result-row"><span className="result-key">alerts[0].message</span><span className="result-val" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{data?.alerts?.[0]?.message || "N/A"}</span></div>
          )}
        </motion.div>
      )}
    </div>
  );
};

// ── 5. get_isp_rating — GET /api/v1/isp-rating ────────────────────
const GetISPRatingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await get_isp_rating()); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="My ISP Rating" endpoint="Locally calculated score for your provider" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Loading…</> : '⭐ My ISP Rating'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="rating-grid">
            <div className="rating-item"><div className="rating-score">{data?.overall_score || 0}</div><div className="rating-label">overall_score</div></div>
            <div className="rating-item"><div className="rating-score">{data?.speed_score || 0}</div><div className="rating-label">speed_score</div></div>
            <div className="rating-item"><div className="rating-score">{data?.reliability_score || 0}</div><div className="rating-label">reliability_score</div></div>
            <div className="rating-item"><div className="rating-score">{data?.value_score || 0}</div><div className="rating-label">value_score</div></div>
          </div>
          <div className="result-box" style={{ marginTop: '0.75rem' }}>
            <div className="result-row">
              <span className="result-key">comparison_to_area</span>
              <span className="result-val safe">{data?.comparison_to_area?.replace('_', ' ') || "N/A"}</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

// ── 6. predict_throttling — GET /api/v1/predict-throttling ──────────────────
const PredictThrottlingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await predict_throttling()); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="Throttling Predictor" endpoint="Machine learning future projections" live />
      <button className="api-btn api-btn-outline" style={{ maxWidth: 300 }} onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Predicting…</> : '🔮 Predict Throttling'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      
      {data?.predictions && !data?.error && (
        <motion.div className="predict-list" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {data?.predictions?.map((p, i) => {
            const high = p.probability > 70;
            const med = p.probability >= 40 && p.probability <= 70;
            const colorCode = high ? '#ff4d4d' : med ? '#ffa500' : '#00c864';
            
            return (
              <div key={i} className={`predict-cell ${high ? 'high-risk' : ''}`}>
                <div className="predict-hour">{p.time}</div>
                <div className="predict-prob" style={{ color: colorCode }}>{p.probability}%</div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginTop: 4, textAlign: 'center' }}>{p.type}</div>
              </div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
};

// ── 7. get_isp_rankings — GET /api/v1/isp-rankings ──────────────
const GetISPRankingsPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    get_isp_rankings()
      .then(res => setData(res))
      .catch(e => setError(e.message || "Failed"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="ISP Rankings" endpoint="Crowdsourced ISP performance data" live />
      {loading && <div className="panel-loading"><Spinner /> Loading rankings…</div>}
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && data.length > 0 && (
        <motion.table className="isp-table" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Provider</th>
              <th>Avg Speed (Mbps)</th>
              <th>Reliability (%)</th>
              <th>User Rating</th>
            </tr>
          </thead>
          <tbody>
            {data.map((isp, i) => (
              <motion.tr key={isp.rank || i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}>
                <td><span className="isp-rank">#{isp.rank || '-'}</span></td>
                <td>{isp.name || 'Unknown'}</td>
                <td>
                  {isp.avg_speed || 0}
                  <div className="isp-bar-track"><div className="isp-bar-fill" style={{ width: `${Math.min((isp.avg_speed || 0)/20, 100)}%` }} /></div>
                </td>
                <td>{isp.reliability || 0}%</td>
                <td>{'★'.repeat(Math.round(isp.user_rating || 0))} {isp.user_rating || 0}</td>
              </motion.tr>
            ))}
          </tbody>
        </motion.table>
      )}
    </div>
  );
};

// ── 8. get_network_logs — GET /api/v1/logs ──────────────────────────
const GetNetworkLogsPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async () => {
    if (loading && !data) return; // Only block if we have no data at all
    setLoading(!data); // Show spinner only on initial load
    try { setData(await get_network_logs()); setError(null); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, [loading, data]);

  // Poll for new logs every 8 seconds
  useInterval(() => { fetchLogs(); }, 8000);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="Recent Network Logs" endpoint="Audit trail of previous measurements" live />
      <button className="api-btn api-btn-outline" style={{ maxWidth: 300 }} onClick={fetchLogs} disabled={loading}>
        {loading ? <><Spinner /> Fetching…</> : '📋 Recent Network Logs'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && data.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <table className="logs-table">
            <thead>
              <tr>
                <th>timestamp</th>
                <th>download_speed</th>
                <th>upload_speed</th>
                <th>ping</th>
                <th>download_ratio</th>
              </tr>
            </thead>
            <tbody>
              {data.map((log, i) => (
                <tr key={log.id || i}>
                  <td>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'N/A'}</td>
                  <td>{log.download_speed || 0} Mbps</td>
                  <td>{log.upload_speed || 0} Mbps</td>
                  <td>{log.ping || 0} ms</td>
                  <td style={{ color: (log.download_ratio || 0) < 0.8 ? '#ff4d4d' : '#00c864' }}>
                    {Math.round((log.download_ratio || 0) * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </div>
  );
};

// ── 9. generate_report — POST /api/v1/generate-report ──────────────────────
const GenerateReportPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await generate_report()); }
    catch (e) { setError(e.message || "Failed"); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="Generate Legal Report" endpoint="Evidence package for regulatory complaints" live />
      <button className="api-btn api-btn-primary" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Generating…</> : '📄 Generate Legal Report'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="report-badge">{data?.status || 'N/A'}</div>
          <div className="result-row"><span className="result-key">id</span><span className="result-val" style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary-accent)', fontSize: '0.75rem' }}>{data?.id || 'N/A'}</span></div>
          <div className="result-row"><span className="result-key">title</span><span className="result-val" style={{ fontSize: '0.72rem', maxWidth: '60%', textAlign: 'right' }}>{data?.title || 'N/A'}</span></div>
          <div className="result-row"><span className="result-key">summary.total_tests</span><span className="result-val">{data?.summary?.total_tests || 0}</span></div>
          <div className="result-row"><span className="result-key">summary.throttling_events</span><span className="result-val danger">{data?.summary?.throttling_events || 0}</span></div>
          <div className="result-row"><span className="result-key">summary.avg_speed_delivery</span><span className="result-val">{data?.summary?.avg_speed_delivery || 0}%</span></div>
          <div className="result-row"><span className="result-key">summary.compliance_score</span><span className={`result-val ${data?.summary?.compliance_score < 0.6 ? 'danger' : 'warn'}`}>{data?.summary?.compliance_score || 0}</span></div>
        </motion.div>
      )}
    </div>
  );
};

// ── Main Export ───────────────────────────────────────────────────────────────
const LiveDashboard = () => {
  return (
    <section className="live-dashboard-section container" id="dashboard">
      <motion.h2
        className="section-title"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        Live <span style={{ color: 'var(--primary-accent)' }}>API Dashboard</span>
      </motion.h2>

      <div className="dashboard-grid">

        {/* Row 1: Speed Test + Throttle Analyze */}
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5 }}>
          <RunSpeedTestPanel />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.1 }}>
          <AnalyzeThrottlingPanel />
        </motion.div>

        {/* Row 2: Quick Check + Dashboard Summary */}
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.15 }}>
          <GetQuickCheckPanel />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.2 }}>
          <GetDashboardSummaryPanel />
        </motion.div>

        {/* Row 3: ISP Rating + Generate Report */}
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.25 }}>
          <GetISPRatingPanel />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.3 }}>
          <GenerateReportPanel />
        </motion.div>

        {/* Full-width: Predict Throttling */}
        <motion.div className="dashboard-grid-full" initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.35 }}>
          <PredictThrottlingPanel />
        </motion.div>

        {/* Full-width: ISP Rankings (auto-loads) */}
        <motion.div className="dashboard-grid-full" initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.4 }}>
          <GetISPRankingsPanel />
        </motion.div>

        {/* Full-width: Network Logs */}
        <motion.div className="dashboard-grid-full" initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.45 }}>
          <GetNetworkLogsPanel />
        </motion.div>

      </div>
    </section>
  );
};

export default LiveDashboard;
