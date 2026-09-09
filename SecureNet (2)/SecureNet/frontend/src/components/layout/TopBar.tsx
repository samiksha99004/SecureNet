/**
 * SecureNet — TopBar
 *
 * Fixed top bar with:
 *  - Mobile menu toggle
 *  - Page title (passed as prop)
 *  - Connection status indicator (WebSocket)
 *  - User display name
 *  - Logout button
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { ConnectionIndicator } from './ConnectionIndicator';
import styles from './TopBar.module.css';

interface TopBarProps {
  title: string;
  onMenuClick: () => void;
}

export function TopBar({ title, onMenuClick }: TopBarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  return (
    <header className={styles.topbar} role="banner">
      {/* Left: mobile menu + page title */}
      <div className={styles.left}>
        <button
          className={styles.menuButton}
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          aria-haspopup="true"
        >
          <Menu size={20} />
        </button>
        <h1 className={styles.pageTitle}>{title}</h1>
      </div>

      {/* Right: connection status + user + logout */}
      <div className={styles.right}>
        <ConnectionIndicator />

        {user && (
          <div className={styles.userChip}>
            <div className={styles.avatar} aria-hidden="true">
              {user.fullName.charAt(0).toUpperCase()}
            </div>
            <span className={styles.userName}>{user.fullName}</span>
          </div>
        )}

        <button
          className={styles.logoutButton}
          onClick={handleLogout}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
