"""장 시작 전 candidates 캐시 프리워밍."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rules.engine import run as run_engine
from src.data import storage

result = run_engine(ignore_holdings=True)
storage.save_engine_cache(result)
print(f"캐시 저장 완료: {result['run_date']}, candidates={len(result['candidates'])}")
