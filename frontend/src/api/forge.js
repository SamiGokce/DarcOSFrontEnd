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

export const listSouls = () => forge('/souls/');
export const getSoul = (slug) => forge(`/souls/${slug}/`);
export const listMemories = (slug) => forge(`/souls/${slug}/memories/`);
export const createSoul = (name) => forge('/souls/', { method: 'POST', body: { name } });
export const saveSoul = (slug, content, flags, person) =>
  forge(`/souls/${slug}/`, { method: 'PUT', body: { content, flags, person } });
export const deleteSoul = (slug) => forge(`/souls/${slug}/`, { method: 'DELETE' });

export const listChats = (soul) => forge(soul ? `/chats/?soul=${encodeURIComponent(soul)}` : '/chats/');
export const getChat = (id) => forge(`/chats/${id}/`);
export const createChat = (soul, modelId) => forge('/chats/', { method: 'POST', body: { soul, model_id: modelId } });
export const deleteChat = (id) => forge(`/chats/${id}/`, { method: 'DELETE' });
export const sendMessage = (id, content, sampling, safetyFilter = true) =>
  forge(`/chats/${id}/messages/`, { method: 'POST', body: { content, sampling, safety_filter: safetyFilter } });

export const modelStatus = () => forge('/model/');
export const modelCard = (repoId) => forge(`/model-card/?repo_id=${encodeURIComponent(repoId)}`);
export const recallStatus = () => forge('/recall/');
export const saveRecall = (kind) => forge('/recall/', { method: 'POST', body: { kind } });
export const loadModel = () => forge('/model/', { method: 'POST' });
export const listModels = () => forge('/models/');
export const createModel = (model) => forge('/models/', { method: 'POST', body: model });
export const downloadModel = (id) => forge(`/models/${id}/download/`, { method: 'POST' });
export const loadRegisteredModel = (id) => forge(`/models/${id}/load/`, { method: 'POST' });
export const uninstallModel = (id) => forge(`/models/${id}/uninstall/`, { method: 'POST' });
export const saveHuggingFaceToken = (token) => forge('/huggingface/', { method: 'POST', body: { token } });
