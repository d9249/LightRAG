#!/usr/bin/env node
/**
 * 데이터셋 목록을 자동으로 스캔해서 JSON 파일로 생성하는 스크립트
 */

import fs from 'fs'
import path from 'path'

const DATA_DIR = path.join(process.cwd(), 'data')
const OUTPUT_FILE = path.join(process.cwd(), 'src', 'datasets.json')

function scanDatasets() {
  console.log('🔍 Scanning datasets in:', DATA_DIR)
  
  try {
    if (!fs.existsSync(DATA_DIR)) {
      console.error('❌ Data directory not found:', DATA_DIR)
      return []
    }

    const datasets = []
    const folders = fs.readdirSync(DATA_DIR, { withFileTypes: true })
    
    for (const folder of folders) {
      if (folder.isDirectory()) {
        const datasetName = folder.name
        const entitiesFile = path.join(DATA_DIR, datasetName, 'kv_store_full_entities.json')
        const relationsFile = path.join(DATA_DIR, datasetName, 'kv_store_full_relations.json')
        
        if (fs.existsSync(entitiesFile) && fs.existsSync(relationsFile)) {
          datasets.push(datasetName)
          console.log(`✅ Valid dataset found: ${datasetName}`)
        } else {
          console.log(`⚠️ Invalid dataset (missing files): ${datasetName}`)
        }
      }
    }
    
    return datasets.sort()
  } catch (error) {
    console.error('❌ Error scanning datasets:', error)
    return []
  }
}

function generateDatasetsFile() {
  const datasets = scanDatasets()
  
  const datasetsInfo = {
    datasets: datasets,
    default: datasets.length > 0 ? datasets[0] : null,
    generated: new Date().toISOString(),
    total: datasets.length
  }
  
  // 출력 디렉토리 생성
  const outputDir = path.dirname(OUTPUT_FILE)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }
  
  // JSON 파일 생성
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(datasetsInfo, null, 2))
  
  console.log('📄 Generated datasets file:', OUTPUT_FILE)
  console.log('📊 Found datasets:', datasets)
  console.log('🎯 Default dataset:', datasetsInfo.default)
  
  return datasetsInfo
}

// 실행
if (import.meta.url === `file://${process.argv[1]}`) {
  generateDatasetsFile()
}
