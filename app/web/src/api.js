// The browser runs outside the compose network and cannot resolve "api",
// so the base URL is supplied at build time rather than hardcoded.
export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} returned HTTP ${res.status}`)
  return res.json()
}

export const getCategories = () => get('/api/categories')
export const getZones = () => get('/api/zones')
export const getExistingLayout = () => get('/api/layout/existing')
export const getProposedLayout = () => get('/api/layout/proposed')
export const getOptimalLayout = (constrained = true) =>
  get(`/api/layout/optimal?constrained=${constrained}`)

export async function scoreLayout(assignment) {
  const res = await fetch(`${API_BASE}/api/layout/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assignment }),
  })
  if (!res.ok) throw new Error(`scoring returned HTTP ${res.status}`)
  return res.json()
}
