import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { modelStatus } from '../api/forge';
import { useAuth } from '../context/AuthContext';
import styles from '../components/Section.module.css';

export default function Settings() {
  const { part } = useParams();
  const { user, isAuthenticated } = useAuth();
  const [model, setModel] = useState(null);
  const [kernel, setKernel] = useState('checking');

  useEffect(() => {
    if (part !== 'runtime') return undefined;
    modelStatus().then(setModel).catch(() => setModel(null));
    fetch('/kernel/agents')
      .then((response) => setKernel(response.ok ? 'online' : 'offline'))
      .catch(() => setKernel('offline'));
    return undefined;
  }, [part]);

  return (
    <div className={styles.page}>
      <h1 className="page__title">{part === 'runtime' ? 'Runtime' : 'Account'}</h1>
      {part === 'runtime' ? (
        <section className="glass glass-panel">
          <p className={styles.lead}>Kernel: {kernel}.</p>
          <p className={styles.lead}>
            Model: {model ? `${model.model}, ${model.context_tokens} token context, ${model.state}` : 'unavailable'}.
          </p>
        </section>
      ) : (
        <section className="glass glass-panel">
          <p className={styles.lead}>
            {isAuthenticated ? `Signed in as ${user.username}.` : 'Signed in.'}
          </p>
        </section>
      )}
    </div>
  );
}
