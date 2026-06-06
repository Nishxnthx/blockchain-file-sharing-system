import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/login': 'http://localhost:5000',
            '/logout': 'http://localhost:5000',
            '/upload': 'http://localhost:5000',
            '/verify_report': 'http://localhost:5000',
            '/download': 'http://localhost:5000'
        }
    }
})
