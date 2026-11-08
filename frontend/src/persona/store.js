export const FIGURE_SECTIONS = ['figures'];

export const SOUL_CHANGED = 'basalisk:soul-changed';
export const CHAT_CHANGED = 'basalisk:chat-changed';

export const announceSoulChange = () => window.dispatchEvent(new Event(SOUL_CHANGED));
export const announceChatChange = () => window.dispatchEvent(new Event(CHAT_CHANGED));
