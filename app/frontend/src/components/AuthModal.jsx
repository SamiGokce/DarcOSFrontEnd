import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import styles from './AuthModal.module.css';

export default function AuthModal({ mode, onClose, onSwitchMode }) {
  const { login, register } = useAuth();
  const isLogin = mode === 'login';

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isLogin) {
        await login(username.trim(), password);
      } else {
        await register({
          username: username.trim(),
          email: email.trim(),
          password,
          password_confirm: passwordConfirm,
        });
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <div
        className={`glass ${styles.modal}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
          ×
        </button>

        <h2 id="auth-modal-title" className={styles.title}>
          {isLogin ? 'Log in' : 'Sign up'}
        </h2>
        <p className={styles.subtitle}>
          {isLogin
            ? 'Use your DarcOS account.'
            : 'Create an account with Django authentication.'}
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label}>
            Username
            <input
              className="field"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>

          {!isLogin && (
            <label className={styles.label}>
              Email
              <input
                className="field"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}

          <label className={styles.label}>
            Password
            <input
              className="field"
              type="password"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          {!isLogin && (
            <label className={styles.label}>
              Confirm password
              <input
                className="field"
                type="password"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
              />
            </label>
          )}

          {error && <p className={styles.error}>{error}</p>}

          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Please wait…' : isLogin ? 'Log in' : 'Sign up'}
          </button>
        </form>

        <p className={styles.switch}>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            type="button"
            className={styles.switchBtn}
            onClick={() => onSwitchMode(isLogin ? 'signup' : 'login')}
          >
            {isLogin ? 'Sign up' : 'Log in'}
          </button>
        </p>
      </div>
    </div>
  );
}
