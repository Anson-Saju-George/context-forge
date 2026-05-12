import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'

const envPath = 'backend/.env'
const backendEnv = fs.existsSync(envPath)
  ? Object.fromEntries(
      fs.readFileSync(envPath, 'utf-8')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line && !line.startsWith('#') && line.includes('='))
        .map((line) => {
          const [key, ...value] = line.split('=')
          return [key.trim(), value.join('=').trim().replace(/^['"]|['"]$/g, '')]
        }),
    )
  : {}
const rawBase = backendEnv.FRONTEND_BASE_PATH || '/'
const mountPath = rawBase === '/' ? '/' : `/${rawBase.replace(/^\/|\/$/g, '')}`
const base = mountPath === '/' ? '/' : `${mountPath}/`

function baseRedirectPlugin() {
  return {
    name: 'contextforge-base-redirect',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (mountPath !== '/' && request.url === mountPath) {
          response.statusCode = 302
          response.setHeader('Location', base)
          response.end()
          return
        }

        next()
      })
    },
  }
}

export default defineConfig({
  base,
  plugins: [baseRedirectPlugin(), react(), tailwindcss()],
  server: {
    watch: {
      ignored: [
        '**/backend/reports/**',
        '**/backend/data/**',
        '**/data/**',
        '**/__pycache__/**',
      ],
    },
  },
})
