/**
 * SecureNet — Electron shell
 *
 * Starts the FastAPI backend (from backend/venv) and opens the dashboard.
 *  - Production (`npm start`): the backend serves the built frontend
 *    (frontend/dist) on http://localhost:8000, so routing, the API and the
 *    WebSocket all share one origin (no file:// or CORS problems).
 *  - Development (`npm run dev`): loads the Vite dev server on :5173.
 *
 * If a backend is already running on :8000 it is reused, not restarted.
 * Override locations with SECURENET_BACKEND_DIR / SECURENET_FRONTEND_DIST
 * (needed for an electron-builder package, which does not bundle Python).
 */

const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

const isDev = process.argv.includes('--dev');
const BACKEND_HOST = 'localhost';
const BACKEND_PORT = 8000;
const BACKEND_DIR =
  process.env.SECURENET_BACKEND_DIR || path.resolve(__dirname, '..', '..', 'backend');
const FRONTEND_DIST =
  process.env.SECURENET_FRONTEND_DIST || path.resolve(__dirname, '..', '..', 'frontend', 'dist');
const APP_URL = isDev ? 'http://localhost:5173' : `http://${BACKEND_HOST}:${BACKEND_PORT}/`;

let mainWindow = null;
let backendProcess = null;

/** Resolve true when GET /health answers (backend is up). */
function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.request(
      { host: BACKEND_HOST, port: BACKEND_PORT, path: '/health', method: 'GET', timeout: 2000 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      }
    );
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

function pythonExecutable() {
  const venvPython =
    process.platform === 'win32'
      ? path.join(BACKEND_DIR, 'venv', 'Scripts', 'python.exe')
      : path.join(BACKEND_DIR, 'venv', 'bin', 'python');
  return fs.existsSync(venvPython) ? venvPython : 'python';
}

async function startBackend() {
  if (await checkBackendHealth()) {
    console.log('[Electron] Reusing backend already running on port', BACKEND_PORT);
    return;
  }
  if (!fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py'))) {
    throw new Error(`Backend not found at ${BACKEND_DIR} (set SECURENET_BACKEND_DIR).`);
  }

  const env = { ...process.env };
  if (!isDev) {
    if (!fs.existsSync(path.join(FRONTEND_DIST, 'index.html'))) {
      throw new Error('frontend/dist is missing — run "npm run build:frontend" in the desktop folder first.');
    }
    env.FRONTEND_DIST = FRONTEND_DIST;
  }

  console.log('[Electron] Starting backend in', BACKEND_DIR);
  backendProcess = spawn(
    pythonExecutable(),
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT), '--ws-max-size', '65536', '--no-server-header'],
    { cwd: BACKEND_DIR, env, stdio: 'pipe', windowsHide: true }
  );
  backendProcess.stdout.on('data', (d) => console.log(`[Backend] ${d.toString().trim()}`));
  backendProcess.stderr.on('data', (d) => console.log(`[Backend] ${d.toString().trim()}`));

  const exited = new Promise((_, reject) => {
    backendProcess.on('error', reject);
    backendProcess.on('close', (code) => reject(new Error(`Backend exited with code ${code}`)));
  });

  const ready = (async () => {
    for (let attempt = 1; attempt <= 60; attempt++) {
      if (await checkBackendHealth()) return;
      await new Promise((r) => setTimeout(r, 1000));
    }
    throw new Error('Backend did not become ready within 60 seconds');
  })();

  await Promise.race([ready, exited]);
  console.log('[Electron] Backend is ready');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    backgroundColor: '#0a1020', // dark theme — no white flash while loading
    title: 'SecureNet IDS',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  mainWindow.loadURL(APP_URL);
  if (isDev) mainWindow.webContents.openDevTools();
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function stopBackend() {
  if (backendProcess) {
    console.log('[Electron] Stopping backend...');
    backendProcess.kill();
    backendProcess = null;
  }
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    createWindow();
  } catch (error) {
    console.error('[Electron] Startup failed:', error);
    dialog.showErrorBox('SecureNet could not start', String(error.message || error));
    stopBackend();
    app.quit();
  }
});

app.on('window-all-closed', () => {
  stopBackend();
  app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

app.on('before-quit', stopBackend);
