import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// 빌드 시 자동으로 데이터 복사하는 플러그인
const copyDataPlugin = () => {
  return {
    name: 'copy-data',
    writeBundle() {
      // 1. datasets.json 생성
      const dataDir = path.join(process.cwd(), 'data')
      const distDir = path.join(process.cwd(), 'dist')
      
      console.log('🔄 Generating datasets.json...')
      
      if (fs.existsSync(dataDir)) {
        const datasets = []
        const folders = fs.readdirSync(dataDir, { withFileTypes: true })
        
        for (const folder of folders) {
          if (folder.isDirectory()) {
            const entitiesFile = path.join(dataDir, folder.name, 'kv_store_full_entities.json')
            const relationsFile = path.join(dataDir, folder.name, 'kv_store_full_relations.json')
            
            if (fs.existsSync(entitiesFile) && fs.existsSync(relationsFile)) {
              datasets.push(folder.name)
              console.log(`✅ Dataset: ${folder.name}`)
            }
          }
        }
        
        const datasetsInfo = {
          datasets: datasets.sort(),
          default: datasets[0] || null,
          generated: new Date().toISOString(),
          total: datasets.length
        }
        
        fs.writeFileSync(path.join(distDir, 'datasets.json'), JSON.stringify(datasetsInfo, null, 2))
        console.log(`📄 Generated datasets.json with ${datasets.length} datasets`)
      }
      
      // 2. data 폴더 복사
      console.log('📂 Copying data folder...')
      if (fs.existsSync(dataDir)) {
        const distDataDir = path.join(distDir, 'data')
        if (fs.existsSync(distDataDir)) {
          fs.rmSync(distDataDir, { recursive: true })
        }
        fs.cpSync(dataDir, distDataDir, { recursive: true })
        console.log('✅ Data folder copied to dist/')
      }
    }
  }
}

export default defineConfig({
  plugins: [react(), copyDataPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './', // 상대 경로로 설정하여 HTML 파일 직접 열기 가능
  build: {
    outDir: 'dist',
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
