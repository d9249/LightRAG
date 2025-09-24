#!/usr/bin/env python3
"""
데이터셋 목록을 자동으로 스캔해서 JSON 파일로 생성하는 스크립트
"""

import os
import json
from pathlib import Path
from datetime import datetime

def scan_datasets():
    """data 폴더를 스캔해서 유효한 데이터셋 목록 반환"""
    
    current_dir = Path(__file__).parent.parent
    data_dir = current_dir / 'data'
    
    print(f"🔍 Scanning datasets in: {data_dir}")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return []
    
    datasets = []
    
    try:
        # data 폴더 내의 모든 폴더 검사
        for item in data_dir.iterdir():
            if item.is_dir():
                dataset_name = item.name
                entities_file = item / 'kv_store_full_entities.json'
                relations_file = item / 'kv_store_full_relations.json'
                
                if entities_file.exists() and relations_file.exists():
                    datasets.append(dataset_name)
                    print(f"✅ Valid dataset found: {dataset_name}")
                else:
                    print(f"⚠️ Invalid dataset (missing files): {dataset_name}")
        
        return sorted(datasets)
        
    except Exception as e:
        print(f"❌ Error scanning datasets: {e}")
        return []

def generate_datasets_json():
    """데이터셋 정보를 JSON 파일로 생성"""
    
    datasets = scan_datasets()
    
    datasets_info = {
        "datasets": datasets,
        "default": datasets[0] if datasets else None,
        "generated": datetime.now().isoformat(),
        "total": len(datasets)
    }
    
    # 출력 파일 경로
    current_dir = Path(__file__).parent.parent
    output_file = current_dir / 'src' / 'datasets.json'
    
    # src 디렉토리 생성 (없으면)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON 파일 생성
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(datasets_info, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Generated datasets file: {output_file}")
    print(f"📊 Found datasets: {datasets}")
    print(f"🎯 Default dataset: {datasets_info['default']}")
    
    # dist 폴더에도 복사 (빌드된 앱에서 사용)
    dist_file = current_dir / 'dist' / 'datasets.json'
    if dist_file.parent.exists():
        with open(dist_file, 'w', encoding='utf-8') as f:
            json.dump(datasets_info, f, ensure_ascii=False, indent=2)
        print(f"📄 Copied to dist: {dist_file}")
    
    return datasets_info

if __name__ == "__main__":
    print("🚀 Dataset Scanner 시작!")
    print("=" * 50)
    
    result = generate_datasets_json()
    
    if result['total'] > 0:
        print(f"\n🎉 {result['total']}개 데이터셋 발견!")
        print(f"📋 목록: {', '.join(result['datasets'])}")
    else:
        print("\n❌ 유효한 데이터셋을 찾을 수 없습니다.")
        print("💡 data 폴더에 각 데이터셋별로 다음 파일들이 필요합니다:")
        print("   • kv_store_full_entities.json")
        print("   • kv_store_full_relations.json")
