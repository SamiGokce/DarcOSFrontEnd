import { useEffect, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { listChats, listSouls } from '../api/forge';
import { CHAT_CHANGED, SOUL_CHANGED } from '../persona/store';
import bar from './SecondaryBar.module.css';

export default function ChatList() {
  const { search } = useLocation();
  const [params] = useSearchParams();
  const selected = params.get('chat');
  const soul = params.get('soul');
  const [chats, setChats] = useState([]);
  const [names, setNames] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    const read = () => {
      listChats()
        .then((rows) => {
          setChats(rows);
          setError('');
        })
        .catch((err) => setError(err.message));
      listSouls()
        .then((rows) => setNames(Object.fromEntries(rows.map((row) => [row.slug, row.name]))))
        .catch(() => {});
    };
    read();
    window.addEventListener(CHAT_CHANGED, read);
    window.addEventListener(SOUL_CHANGED, read);
    return () => {
      window.removeEventListener(CHAT_CHANGED, read);
      window.removeEventListener(SOUL_CHANGED, read);
    };
  }, [search]);

  return (
    <aside className={bar.bar} aria-label="Chats">
      <div className={bar.title}>Chats</div>
      <Link to={soul ? `/?soul=${encodeURIComponent(soul)}` : '/'} className={!selected ? `${bar.link} ${bar.linkActive}` : bar.link}>
        <span className={bar.linkName}>＋ New chat</span>
      </Link>
      {chats.map((chat) => (
        <Link
          key={chat.id}
          to={`/?chat=${chat.id}`}
          className={String(chat.id) === String(selected) ? `${bar.link} ${bar.linkActive}` : bar.link}
        >
          <span className={bar.linkName}>{chat.title || 'Untitled'}</span>
          <span className={bar.linkMeta}>
            {names[chat.soul] || chat.soul} · {chat.model_name} · {chat.message_count}
          </span>
        </Link>
      ))}
      {error && <div className={bar.offline}>{error}</div>}
    </aside>
  );
}
