import React, { useEffect, useState, useCallback } from 'react';
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

// ── 1. run_speed_test — POST /api/v1/network/speed-test ─────────────────────
const RunSpeedTestPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null); setData(null);
    try { setData(await run_speed_test()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="run_speed_test()" endpoint="POST /api/v1/network/speed-test" live />
      <button className="api-btn api-btn-primary" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Running…</> : '▶ run_speed_test()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="speed-cards" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="speed-card">
            <div className="speed-card-val">{data.download_speed}</div>
            <div className="speed-card-label">download_speed (Mbps)</div>
          </div>
          <div className="speed-card">
            <div className="speed-card-val">{data.upload_speed}</div>
            <div className="speed-card-label">upload_speed (Mbps)</div>
          </div>
          <div className="speed-card">
            <div className="speed-card-val">{data.latency}</div>
            <div className="speed-card-label">latency (ms)</div>
          </div>
          <div className="result-box" style={{ gridColumn: '1/-1', marginTop: 0 }}>
            <div className="result-row">
              <span className="result-key">server</span>
              <span className="result-val">{data.server}</span>
            </div>
            <div className="result-row">
              <span className="result-key">timestamp</span>
              <span className="result-val" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                {new Date(data.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

// ── 2. analyze_throttling — POST /api/v1/throttling/analyze ─────────────────
const AnalyzeThrottlingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null); setData(null);
    try { setData(await analyze_throttling()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="analyze_throttling()" endpoint="POST /api/v1/throttling/analyze" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Analysing…</> : '⚡ analyze_throttling()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row">
            <span className="result-key">throttling_detected</span>
            <span className={`result-val ${data.throttling_detected ? 'danger' : 'safe'}`}>
              {String(data.throttling_detected)}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">type</span>
            <span className="result-val">{data.type}</span>
          </div>
          <div className="result-row">
            <span className="result-key">severity</span>
            <span className={`result-val ${data.severity === 'high' ? 'danger' : data.severity === 'medium' ? 'warn' : ''}`}>
              {data.severity}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">affected_services</span>
            <span className="result-val" style={{ fontSize: '0.75rem' }}>
              {data.affected_services.length ? data.affected_services.join(', ') : '—'}
            </span>
          </div>
          <div className="result-row">
            <span className="result-key">recommendation</span>
            <span className="result-val" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', maxWidth: '55%', textAlign: 'right' }}>
              {data.recommendation}
            </span>
          </div>
          <div className="conf-bar-wrap">
            <div className="conf-bar-fill" style={{ width: `${Math.round(data.confidence * 100)}%` }} />
          </div>
          <p style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
            confidence: {Math.round(data.confidence * 100)}%
          </p>
        </motion.div>
      )}
    </div>
  );
};

// ── 3. get_quick_check — GET /api/v1/throttling/quick-check ─────────────────
const GetQuickCheckPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null); setData(null);
    try { setData(await get_quick_check()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="get_quick_check()" endpoint="GET /api/v1/throttling/quick-check" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Checking…</> : '🔍 get_quick_check()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row">
            <span className="result-key">status</span>
            <span className={`result-val ${data.status === 'clear' ? 'safe' : 'danger'}`}>{data.status}</span>
          </div>
          <div className="result-row">
            <span className="result-key">analysis.explanation</span>
            <span className="result-val" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {data.analysis?.explanation}
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

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await get_dashboard_summary()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="get_dashboard_summary()" endpoint="GET /api/v1/dashboard/summary" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Loading…</> : '📊 get_dashboard_summary()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="result-row"><span className="result-key">current_speed.download</span><span className="result-val">{data.current_speed.download} Mbps</span></div>
          <div className="result-row"><span className="result-key">current_speed.upload</span><span className="result-val">{data.current_speed.upload} Mbps</span></div>
          <div className="result-row"><span className="result-key">current_speed.latency</span><span className="result-val">{data.current_speed.latency} ms</span></div>
          <div className="result-row"><span className="result-key">promised_speed</span><span className="result-val">{data.promised_speed} Mbps</span></div>
          <div className="result-row"><span className="result-key">speed_delivery_rate</span><span className={`result-val ${data.speed_delivery_rate < 0.7 ? 'danger' : 'safe'}`}>{Math.round(data.speed_delivery_rate * 100)}%</span></div>
          <div className="result-row"><span className="result-key">throttling_status.active</span><span className={`result-val ${data.throttling_status.active ? 'danger' : 'safe'}`}>{String(data.throttling_status.active)}</span></div>
          {data.alerts?.length > 0 && (
            <div className="result-row"><span className="result-key">alerts[0].message</span><span className="result-val" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{data.alerts[0].message}</span></div>
          )}
        </motion.div>
      )}
    </div>
  );
};

// ── 5. get_isp_rating — GET /api/v1/dashboard/isp-rating ────────────────────
const GetISPRatingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await get_isp_rating()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="get_isp_rating()" endpoint="GET /api/v1/dashboard/isp-rating" live />
      <button className="api-btn api-btn-outline" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Loading…</> : '⭐ get_isp_rating()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="rating-grid">
            <div className="rating-item"><div className="rating-score">{data.overall_score}</div><div className="rating-label">overall_score</div></div>
            <div className="rating-item"><div className="rating-score">{data.speed_score}</div><div className="rating-label">speed_score</div></div>
            <div className="rating-item"><div className="rating-score">{data.reliability_score}</div><div className="rating-label">reliability_score</div></div>
            <div className="rating-item"><div className="rating-score">{data.value_score}</div><div className="rating-label">value_score</div></div>
          </div>
          <div className="result-box" style={{ marginTop: '0.75rem' }}>
            <div className="result-row">
              <span className="result-key">comparison_to_area</span>
              <span className="result-val safe">{data.comparison_to_area?.replace('_', ' ')}</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

// ── 6. predict_throttling — GET /api/v1/throttling/predict ──────────────────
const PredictThrottlingPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await predict_throttling()); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="predict_throttling()" endpoint="GET /api/v1/throttling/predict" live />
      <button className="api-btn api-btn-outline" style={{ maxWidth: 300 }} onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Predicting…</> : '🔮 predict_throttling()'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data?.predictions && (
        <motion.div className="predict-list" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {data.predictions.map((p, i) => {
            const hour = new Date(p.hour).getHours();
            const pct  = Math.round(p.throttling_probability * 100);
            const high = pct > 60;
            return (
              <div key={i} className={`predict-cell ${high ? 'high-risk' : ''}`}>
                <div className="predict-hour">{String(hour).padStart(2,'0')}:00</div>
                <div className="predict-prob" style={{ color: high ? '#ff4d4d' : '#aaa' }}>{pct}%</div>
                <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', marginTop: 2 }}>{p.likely_type}</div>
              </div>
            );
          })}
        </motion.div>
      )}
    </div>
  );
};

// ── 7. get_isp_rankings — GET /api/v1/crowdsource/isp-rankings ──────────────
const GetISPRankingsPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    get_isp_rankings()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="get_isp_rankings()" endpoint="GET /api/v1/crowdsource/isp-rankings" live />
      {loading && <div className="panel-loading"><Spinner /> Loading rankings…</div>}
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.table className="isp-table" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <thead>
            <tr>
              <th>rank</th>
              <th>name</th>
              <th>avg_speed (Mbps)</th>
              <th>reliability (%)</th>
              <th>user_rating</th>
            </tr>
          </thead>
          <tbody>
            {data.map((isp, i) => (
              <motion.tr key={isp.rank} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}>
                <td><span className="isp-rank">#{isp.rank}</span></td>
                <td>{isp.name}</td>
                <td>
                  {isp.avg_speed}
                  <div className="isp-bar-track"><div className="isp-bar-fill" style={{ width: `${isp.avg_speed}%` }} /></div>
                </td>
                <td>{isp.reliability}%</td>
                <td>{'★'.repeat(Math.round(isp.user_rating))} {isp.user_rating}</td>
              </motion.tr>
            ))}
          </tbody>
        </motion.table>
      )}
    </div>
  );
};

// ── 8. get_network_logs — GET /api/v1/network/logs ──────────────────────────
const GetNetworkLogsPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await get_network_logs(8)); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel dashboard-grid-full">
      <PanelHeader title="get_network_logs()" endpoint="GET /api/v1/network/logs" live />
      <button className="api-btn api-btn-outline" style={{ maxWidth: 300 }} onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Fetching…</> : '📋 get_network_logs(limit=8)'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
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
              {data.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.timestamp).toLocaleDateString()}</td>
                  <td>{log.download_speed} Mbps</td>
                  <td>{log.upload_speed} Mbps</td>
                  <td>{log.ping} ms</td>
                  <td style={{ color: log.download_ratio < 0.8 ? '#ff4d4d' : '#00c864' }}>
                    {Math.round(log.download_ratio * 100)}%
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

// ── 9. generate_report — POST /api/v1/reports/generate ──────────────────────
const GenerateReportPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleClick = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await generate_report('legal')); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  return (
    <div className="dashboard-panel">
      <PanelHeader title="generate_report()" endpoint="POST /api/v1/reports/generate" live />
      <button className="api-btn api-btn-primary" onClick={handleClick} disabled={loading}>
        {loading ? <><Spinner /> Generating…</> : '📄 generate_report(type=legal)'}
      </button>
      {error && <p className="panel-error">⚠ {error}</p>}
      {data && (
        <motion.div className="result-box" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="report-badge">{data.status}</div>
          <div className="result-row"><span className="result-key">id</span><span className="result-val" style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary-accent)', fontSize: '0.75rem' }}>{data.id}</span></div>
          <div className="result-row"><span className="result-key">title</span><span className="result-val" style={{ fontSize: '0.72rem', maxWidth: '60%', textAlign: 'right' }}>{data.title}</span></div>
          <div className="result-row"><span className="result-key">summary.total_tests</span><span className="result-val">{data.summary.total_tests}</span></div>
          <div className="result-row"><span className="result-key">summary.throttling_events</span><span className="result-val danger">{data.summary.throttling_events}</span></div>
          <div className="result-row"><span className="result-key">summary.avg_speed_delivery</span><span className="result-val">{data.summary.avg_speed_delivery}%</span></div>
          <div className="result-row"><span className="result-key">summary.compliance_score</span><span className={`result-val ${data.summary.compliance_score < 0.6 ? 'danger' : 'warn'}`}>{data.summary.compliance_score}</span></div>
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
      <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '-2rem', marginBottom: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', letterSpacing: '1px' }}>
        All buttons call the FastAPI backend at localhost:8000 — responses shown in real-time
      </p>

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
