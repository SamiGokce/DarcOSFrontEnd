import { apiUrl } from './client';

const ACCESS_KEY = 'darcos_access';
const REFRESH_KEY = 'darcos_refresh';

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function parseJsonResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message =
      data.detail ||
      Object.entries(data)
        .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(' ') : val}`)
        .join(' ') ||
      res.statusText;
    throw new Error(message);
  }
  return data;
}

export async function login(username, password) {
  const res = await fetch(apiUrl('/api/auth/login/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await parseJsonResponse(res);
  setTokens(data);
  return data;
}

export async function register({ username, email, password, password_confirm }) {
  const res = await fetch(apiUrl('/api/auth/register/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password, password_confirm }),
  });
  await parseJsonResponse(res);
  return login(username, password);
}

export async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) throw new Error('No refresh token');

  const res = await fetch(apiUrl('/api/auth/refresh/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  const data = await parseJsonResponse(res);
  setTokens({ access: data.access, refresh: data.refresh ?? refresh });
  return data.access;
}

export async function fetchCurrentUser() {
  const token = getAccessToken();
  if (!token) throw new Error('Not authenticated');

  const res = await fetch(apiUrl('/api/auth/me/'), {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseJsonResponse(res);
}
