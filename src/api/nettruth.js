// Use the Vite proxy in development; fallback to the production URL if needed.
const API_URL = import.meta.env.VITE_API_URL || ""; 
// If API_URL is empty, it uses the same origin as the frontend (which is proxied in vite.config.js)
const BASE = API_URL ? `${API_URL}/api/v1` : "/api/v1";

const get = async (path) => {
  try {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
  } catch (error) {
    console.error(`API GET failed [${path}]:`, error.message);
    return null;  // Never crash the UI
  }
};

const post = async (path, body = {}) => {
  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body || {}),
  };
  
  try {
    const res = await fetch(`${BASE}${path}`, options);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(`${res.status} ${res.statusText}: ${JSON.stringify(errorData.detail || errorData)}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`API POST failed [${path}]:`, error.message);
    return null;  // Never crash the UI
  }
};

// ── NEW BACKEND ROUTES ────────────────────────────────────────────────────────
export const run_speed_test = () => post('/speed-test');

export const analyze_throttling = () => post('/analyze-throttling');

export const get_quick_check = () => get('/quick-check');

export const predict_throttling = () => get('/predict-throttling');

export const get_dashboard_summary = () => get('/dashboard/summary');

export const get_isp_rating = () => get('/isp-rating');

export const get_isp_rankings = () => get('/isp-rankings');

export const get_network_logs = () => get('/logs');

export const generate_report = () => post('/generate-report');

