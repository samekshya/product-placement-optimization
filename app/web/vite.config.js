import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Inside Docker the bind mount events are not always delivered natively,
    // so polling is used to keep hot reload working on Windows hosts.
    watch: { usePolling: true },
  },
})
