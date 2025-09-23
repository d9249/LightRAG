import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './', // 상대 경로로 설정하여 HTML 파일 직접 열기 가능
  build: {
    outDir: '../output/react-build',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // 모든 파일을 하나로 묶어서 완전히 독립적으로 만들기
        manualChunks: undefined,
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name].[ext]'
      }
    }
  }
})
