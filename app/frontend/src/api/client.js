import { getAccessToken, getRefreshToken, refreshAccessToken, clearTokens } from './auth';

const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');

export function apiUrl(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${normalized}`;
}

export async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});

  const token = getAccessToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let res = await fetch(apiUrl(path), {
    credentials: 'same-origin',
    ...options,
    headers,
  });

  if (res.status === 401 && getRefreshToken()) {
    try {
      const access = await refreshAccessToken();
      headers.set('Authorization', `Bearer ${access}`);
      res = await fetch(apiUrl(path), {
        credentials: 'same-origin',
        ...options,
        headers,
      });
    } catch {
      clearTokens();
    }
  }

  return res;
}
