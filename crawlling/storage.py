import json
from datetime import datetime
from typing import List, Dict, Optional

def save_to_json(data: List[Dict[str, Optional[str]]]) -> str:
    '''
    크롤링한 데이터를 JSON 파일로 저장하고 파일명 변환
    '''
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"news_{timestamp}.json"

    # JSON 데이터 저장
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"📋 데이터가 JSON 파일로 저장되었습니다 : {filename}")

    return filename
