/**
 * NetTruth API Service
 * Each function name mirrors the FastAPI function name in demo.py exactly.
 * Proxy: Vite forwards /api/* → http://localhost:8000
 */

const BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : '/api/v1';

const get = async (path) => {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
};

const post = async (path, params = '') => {
  const url = params ? `${BASE}${path}?${params}` : `${BASE}${path}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
};

// ── POST /api/v1/network/speed-test ──────────────────────────────
// Backend fn: run_speed_test()
// Returns: { download_speed, upload_speed, latency, timestamp, server }
export const run_speed_test = () => post('/network/speed-test');

// ── POST /api/v1/throttling/analyze ──────────────────────────────
// Backend fn: analyze_throttling()
// Returns: { throttling_detected, confidence, type, affected_services, severity, recommendation }
export const analyze_throttling = () => post('/throttling/analyze');

// ── GET /api/v1/throttling/quick-check ───────────────────────────
// Backend fn: get_quick_check()
// Returns: { status, analysis: { explanation } }
export const get_quick_check = () => get('/throttling/quick-check');

// ── GET /api/v1/throttling/predict ───────────────────────────────
// Backend fn: predict_throttling()
// Returns: { predictions: [{ hour, throttling_probability, expected_speed_drop, likely_type }] }
export const predict_throttling = () => get('/throttling/predict');

// ── GET /api/v1/dashboard/summary ────────────────────────────────
// Backend fn: get_dashboard_summary()
// Returns: { current_speed, promised_speed, speed_delivery_rate, throttling_status, alerts }
export const get_dashboard_summary = () => get('/dashboard/summary');

// ── GET /api/v1/dashboard/speed-trends ───────────────────────────
// Backend fn: get_speed_trends(hours)
// Returns: [{ timestamp, download_speed, upload_speed }]
export const get_speed_trends = (hours = 24) => get(`/dashboard/speed-trends?hours=${hours}`);

// ── GET /api/v1/dashboard/isp-rating ─────────────────────────────
// Backend fn: get_isp_rating()
// Returns: { overall_score, speed_score, reliability_score, value_score, comparison_to_area }
export const get_isp_rating = () => get('/dashboard/isp-rating');

// ── GET /api/v1/crowdsource/isp-rankings ─────────────────────────
// Backend fn: get_isp_rankings()
// Returns: [{ rank, name, avg_speed, reliability, user_rating }]
export const get_isp_rankings = () => get('/crowdsource/isp-rankings');

// ── GET /api/v1/network/logs ──────────────────────────────────────
// Backend fn: get_network_logs(limit)
// Returns: [{ id, timestamp, download_speed, upload_speed, ping, download_ratio }]
export const get_network_logs = (limit = 10) => get(`/network/logs?limit=${limit}`);

// ── POST /api/v1/reports/generate ────────────────────────────────
// Backend fn: generate_report(report_type)
// Returns: { id, title, type, status, created_at, summary, download_url }
export const generate_report = (report_type = 'legal') =>
  post('/reports/generate', `report_type=${report_type}`);
