// Two processes: FastAPI on 8000, Vite preview of the built SPA on 3000 (proxying /api).
module.exports = {
  apps: [
    {
      name: 'pramana-api',
      cwd: './backend',
      script: '../.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env: { PYTHONPATH: '.', APP_ENV: 'development' },
      watch: false, instances: 1, exec_mode: 'fork',
    },
    {
      name: 'pramana-web',
      cwd: './frontend',
      script: 'npx',
      args: 'vite preview --host 0.0.0.0 --port 3000',
      env: { NODE_ENV: 'production' },
      watch: false, instances: 1, exec_mode: 'fork',
    },
  ],
}
