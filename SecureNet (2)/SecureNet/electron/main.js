const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess;

// Backend configuration
const BACKEND_PATH = path.join(__dirname, '..', '..', '..', 'backend');
const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 8000;
const FRONTEND_DIST = path.join(__dirname, '..', 'frontend', 'dist');

/**
 * Check if backend is ready
 */
function checkBackendHealth() {
  return new Promise((resolve) => {
    const options = {
      host: BACKEND_HOST,
      port: BACKEND_PORT,
      path: '/health',
      method: 'GET',
      timeout: 2000
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const health = JSON.parse(data);
          resolve(health.status === 'ok' || health.status === 'degraded');
        } catch (e) {
          resolve(false);
        }
      });
    });

    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });

    req.end();
  });
}

/**
 * Start backend server
 */
function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('[Electron] Starting backend server...');
    console.log('[Electron] Backend path:', BACKEND_PATH);

    // Start backend using uvicorn
    const isDev = process.argv.includes('--dev');
    
    backendProcess = spawn('python', [
      '-m', 'uvicorn',
      'app.main:app',
      '--host', BACKEND_HOST,
      '--port', BACKEND_PORT.toString()
    ], {
      cwd: BACKEND_PATH,
      stdio: 'pipe'
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`[Backend] ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`[Backend Error] ${data.toString().trim()}`);
    });

    backendProcess.on('error', (error) => {
      console.error('[Electron] Failed to start backend:', error);
      reject(error);
    });

    backendProcess.on('close', (code) => {
      console.log(`[Electron] Backend process exited with code ${code}`);
      if (code !== 0 && code !== null) {
        reject(new Error(`Backend exited with code ${code}`));
      }
    });

    // Wait for backend to be ready
    let attempts = 0;
    const maxAttempts = 30;
    
    const checkHealth = setInterval(async () => {
      attempts++;
      console.log(`[Electron] Checking backend health (attempt ${attempts}/${maxAttempts})...`);
      
      const isReady = await checkBackendHealth();
      
      if (isReady) {
        console.log('[Electron] Backend is ready!');
        clearInterval(checkHealth);
        resolve();
      } else if (attempts >= maxAttempts) {
        console.error('[Electron] Backend failed to start within timeout');
        clearInterval(checkHealth);
        reject(new Error('Backend startup timeout'));
      }
    }, 1000);
  });
}

/**
 * Create the main application window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(FRONTEND_DIST, 'favicon.ico')
  });

  // Load the frontend
  const isDev = process.argv.includes('--dev');
  
  if (isDev) {
    // Development mode: load from Vite dev server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // Production mode: load from dist folder
    mainWindow.loadFile(path.join(FRONTEND_DIST, 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * Terminate backend process
 */
function stopBackend() {
  if (backendProcess) {
    console.log('[Electron] Stopping backend...');
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

// App lifecycle
app.whenReady().then(async () => {
  try {
    // Start backend
    await startBackend();
    
    // Create window
    createWindow();
  } catch (error) {
    console.error('[Electron] Startup failed:', error);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  stopBackend();
  app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('[Electron] Uncaught exception:', error);
});

console.log('[Electron] Application initialized');
