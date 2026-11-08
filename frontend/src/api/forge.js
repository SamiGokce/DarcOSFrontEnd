async function forge(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api/forge${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : `Request failed (${response.status}).`;
    throw new Error(message);
  }
  return data;
}

export const listPersonas = () => forge('/personas/');
export const getPersona = (id) => forge(`/personas/${id}/`);
export const createPersona = (persona) => forge('/personas/', { method: 'POST', body: persona });
export const updatePersona = (id, persona) => forge(`/personas/${id}/`, { method: 'PUT', body: persona });
export const deletePersona = (id) => forge(`/personas/${id}/`, { method: 'DELETE' });
export const modelStatus = () => forge('/model/');
export const loadModel = () => forge('/model/', { method: 'POST' });
export const listModels = () => forge('/models/');
export const createModel = (model) => forge('/models/', { method: 'POST', body: model });
export const downloadModel = (id) => forge(`/models/${id}/download/`, { method: 'POST' });
export const loadRegisteredModel = (id) => forge(`/models/${id}/load/`, { method: 'POST' });
export const moldPrompt = (body) => forge('/mold/', { method: 'POST', body: body });
export const speak = (body) => forge('/speak/', { method: 'POST', body: body });
