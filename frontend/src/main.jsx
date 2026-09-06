import React from 'react';
import { createRoot } from 'react-dom/client';
import { init, miniApp, retrieveLaunchParams } from '@telegram-apps/sdk';
import './styles.css';
import App from './App.jsx';

try {
  init();
  miniApp.mountSync?.();
  miniApp.ready?.();
} catch (error) {
  console.warn('Telegram Mini App SDK init failed; running in browser preview.', error);
}

const launchParams = (() => {
  try { return retrieveLaunchParams(); } catch { return {}; }
})();

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App launchParams={launchParams} />
  </React.StrictMode>,
);
