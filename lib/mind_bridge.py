"""
Spark Mind Bridge: Connect cognitive learning to Mind Lite+

This module bridges Spark's insights to Mind's persistent memory:
    Spark Observes → Cognitive Learning → Mind Stores → Patterns Compound

Features:
- Converts CognitiveInsight to Mind memory format
- Syncs to Mind Lite+ via API
- Handles offline mode (queues for later)
- Tracks synced items to avoid duplicates
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[SPARK] requests not installed - Mind sync disabled")

from .cognitive_learner import CognitiveInsight, CognitiveCategory, get_cognitive_learner
from .ports import MIND_URL


# ============= Configuration =============
MIND_API_URL = MIND_URL
SYNC_STATE_FILE = Path.home() / ".spark" / "mind_sync_state.json"
OFFLINE_QUEUE_FILE = Path.home() / ".spark" / "mind_offline_queue.jsonl"
DEFAULT_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
MAX_CONTENT_CHARS = int(os.environ.get("MIND_MAX_CONTENT_CHARS", "4000"))


class SyncStatus(Enum):
    """Status of a sync operation."""
    SUCCESS = "success"
    OFFLINE = "offline"
    DUPLICATE = "duplicate"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class SyncResult:
    """Result of syncing an insight to Mind."""
    status: SyncStatus
    memory_id: Optional[str] = None
    error: Optional[str] = None
    queued: bool = False


class MindBridge:
    """
    Bridge between Spark's cognitive learning and Mind's persistent memory.
    """
    
    def __init__(self, mind_url: str = MIND_API_URL, user_id: str = DEFAULT_USER_ID):
        self.mind_url = mind_url
        self.user_id = user_id
        self.sync_state = self._load_sync_state()
        
    def _load_sync_state(self) -> Dict[str, Any]:
        """Load sync state from disk."""
        if SYNC_STATE_FILE.exists():
            try:
                return json.loads(SYNC_STATE_FILE.read_text())
            except Exception:
                pass
        return {"synced_hashes": [], "last_sync": None}
    
    def _save_sync_state(self):
        """Save sync state to disk."""
        SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.sync_state["last_sync"] = datetime.now().isoformat()
        SYNC_STATE_FILE.write_text(json.dumps(self.sync_state, indent=2))
    
    def _insight_hash(self, insight: CognitiveInsight) -> str:
        """Generate unique hash for an insight."""
        content = f"{insight.category.value}:{insight.insight}:{insight.context}"
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]
    
    def _is_synced(self, insight: CognitiveInsight) -> bool:
        """Check if insight was already synced."""
        hash_val = self._insight_hash(insight)
        return hash_val in self.sync_state.get("synced_hashes", [])
    
    def _mark_synced(self, insight: CognitiveInsight):
        """Mark insight as synced."""
        hash_val = self._insight_hash(insight)
        if "synced_hashes" not in self.sync_state:
            self.sync_state["synced_hashes"] = []
        if hash_val not in self.sync_state["synced_hashes"]:
            self.sync_state["synced_hashes"].append(hash_val)
            if len(self.sync_state["synced_hashes"]) > 1000:
                self.sync_state["synced_hashes"] = self.sync_state["synced_hashes"][-1000:]
            self._save_sync_state()
    
    def _category_to_temporal_level(self, category: CognitiveCategory) -> int:
        """Map cognitive category to Mind temporal level (1-4)."""
        mapping = {
            CognitiveCategory.SELF_AWARENESS: 4,
            CognitiveCategory.USER_UNDERSTANDING: 4,
            CognitiveCategory.WISDOM: 4,
            CognitiveCategory.REASONING: 3,
            CognitiveCategory.CONTEXT: 3,
            CognitiveCategory.META_LEARNING: 4,
            CognitiveCategory.COMMUNICATION: 3,
            CognitiveCategory.CREATIVITY: 3,
        }
        return mapping.get(category, 3)
    
    def _category_to_content_type(self, category: CognitiveCategory) -> str:
        """Map cognitive category to Mind content type."""
        mapping = {
            CognitiveCategory.SELF_AWARENESS: "self_insight",
            CognitiveCategory.USER_UNDERSTANDING: "user_preference",
            CognitiveCategory.WISDOM: "principle",
            CognitiveCategory.REASONING: "reasoning_pattern",
            CognitiveCategory.CONTEXT: "context_rule",
            CognitiveCategory.META_LEARNING: "meta_insight",
            CognitiveCategory.COMMUNICATION: "communication_style",
            CognitiveCategory.CREATIVITY: "creative_approach",
        }
        return mapping.get(category, "cognitive_learning")
    
    def insight_to_memory(self, insight: CognitiveInsight) -> Dict[str, Any]:
        """Convert CognitiveInsight to Mind memory format."""
        content_parts = [f"[{insight.category.value.upper()}] {insight.insight}"]
        
        if insight.context and insight.context != "General principle":
            content_parts.append(f"Context: {insight.context}")
        
        if insight.evidence:
            # Flatten evidence - handle both strings and lists
            flat_evidence = []
            for e in insight.evidence[:3]:
                if isinstance(e, list):
                    flat_evidence.extend(str(x) for x in e)
                else:
                    flat_evidence.append(str(e))
            evidence_str = "; ".join(flat_evidence[:3])
            content_parts.append(f"Evidence: {evidence_str}")

        if insight.counter_examples:
            # Flatten counter_examples - handle both strings and lists
            flat_counter = []
            for c in insight.counter_examples[:2]:
                if isinstance(c, list):
                    flat_counter.extend(str(x) for x in c)
                else:
                    flat_counter.append(str(c))
            counter_str = "; ".join(flat_counter[:2])
            content_parts.append(f"Exceptions: {counter_str}")
        
        content = "\n".join(content_parts)
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS]
        salience = max(0.5, min(0.95, insight.reliability))
        
        return {
            "user_id": self.user_id,
            "content": content,
            "content_type": self._category_to_content_type(insight.category),
            "temporal_level": self._category_to_temporal_level(insight.category),
            "salience": salience
        }
    
    def _check_mind_health(self) -> bool:
        """Check if Mind API is available."""
        if not HAS_REQUESTS:
            return False
        try:
            response = requests.get(f"{self.mind_url}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def _queue_for_later(self, insight: CognitiveInsight, memory_data: Dict):
        """Queue insight for later sync."""
        OFFLINE_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "insight_hash": self._insight_hash(insight),
            "memory_data": memory_data,
            "category": insight.category.value,
            "insight_text": insight.insight[:200]
        }
        
        with open(OFFLINE_QUEUE_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def sync_insight(self, insight: CognitiveInsight) -> SyncResult:
        """Sync a single cognitive insight to Mind."""
        if not HAS_REQUESTS:
            return SyncResult(status=SyncStatus.DISABLED, error="requests not installed")
        
        if self._is_synced(insight):
            return SyncResult(status=SyncStatus.DUPLICATE)
        
        memory_data = self.insight_to_memory(insight)
        
        if not self._check_mind_health():
            self._queue_for_later(insight, memory_data)
            return SyncResult(status=SyncStatus.OFFLINE, queued=True)
        
        try:
            response = requests.post(
                f"{self.mind_url}/v1/memories/",
                json=memory_data,
                timeout=5
            )
            
            if response.status_code == 201:
                result = response.json()
                self._mark_synced(insight)
                print(f"[SPARK] Synced to Mind: {insight.category.value} - {insight.insight[:50]}...")
                return SyncResult(
                    status=SyncStatus.SUCCESS,
                    memory_id=result.get("memory_id")
                )
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            print(f"[SPARK] Mind sync error: {error_msg}")
            return SyncResult(status=SyncStatus.ERROR, error=error_msg)
                
        except Exception as e:
            self._queue_for_later(insight, memory_data)
            return SyncResult(status=SyncStatus.OFFLINE, queued=True, error=str(e))
    
    def sync_all_insights(self) -> Dict[str, int]:
        """Sync all cognitive insights to Mind."""
        cognitive = get_cognitive_learner()
        stats = {"synced": 0, "duplicate": 0, "queued": 0, "error": 0, "disabled": 0}
        
        for insight in cognitive.insights.values():
            result = self.sync_insight(insight)
            stats[result.status.value] = stats.get(result.status.value, 0) + 1
        
        print(f"[SPARK] Sync complete: {stats}")
        return stats
    
    def process_offline_queue(self) -> int:
        """Process queued items."""
        if not OFFLINE_QUEUE_FILE.exists():
            return 0
        
        if not HAS_REQUESTS or not self._check_mind_health():
            return 0
        
        synced = 0
        remaining = []
        
        with open(OFFLINE_QUEUE_FILE, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    response = requests.post(
                        f"{self.mind_url}/v1/memories/",
                        json=entry["memory_data"],
                        timeout=5
                    )
                    
                    if response.status_code == 201:
                        synced += 1
                        if "synced_hashes" not in self.sync_state:
                            self.sync_state["synced_hashes"] = []
                        self.sync_state["synced_hashes"].append(entry["insight_hash"])
                    else:
                        remaining.append(entry)
                except Exception:
                    remaining.append(entry)
        
        if remaining:
            with open(OFFLINE_QUEUE_FILE, "w") as f:
                for entry in remaining:
                    f.write(json.dumps(entry) + "\n")
        else:
            OFFLINE_QUEUE_FILE.unlink(missing_ok=True)
        
        if synced > 0:
            self._save_sync_state()
            print(f"[SPARK] Processed queue: {synced} synced, {len(remaining)} remaining")
        
        return synced
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant memories from Mind."""
        if not HAS_REQUESTS or not self._check_mind_health():
            return []
        
        try:
            response = requests.post(
                f"{self.mind_url}/v1/memories/retrieve",
                json={"user_id": self.user_id, "query": query, "limit": limit},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json().get("memories", [])
            return []
        except Exception:
            return []
    
    def get_stats(self) -> Dict:
        """Get bridge statistics."""
        queue_size = 0
        if OFFLINE_QUEUE_FILE.exists():
            with open(OFFLINE_QUEUE_FILE, "r") as f:
                queue_size = sum(1 for _ in f)
        
        return {
            "synced_count": len(self.sync_state.get("synced_hashes", [])),
            "last_sync": self.sync_state.get("last_sync"),
            "offline_queue_size": queue_size,
            "mind_available": self._check_mind_health() if HAS_REQUESTS else False,
            "requests_installed": HAS_REQUESTS
        }


# ============= Singleton =============
_mind_bridge: Optional[MindBridge] = None

def get_mind_bridge() -> MindBridge:
    """Get the global Mind bridge instance."""
    global _mind_bridge
    if _mind_bridge is None:
        _mind_bridge = MindBridge()
    return _mind_bridge


# ============= Convenience Functions =============
def sync_insight_to_mind(insight: CognitiveInsight) -> SyncResult:
    """Sync a single insight to Mind."""
    return get_mind_bridge().sync_insight(insight)


def sync_all_to_mind() -> Dict[str, int]:
    """Sync all insights to Mind."""
    return get_mind_bridge().sync_all_insights()


def retrieve_from_mind(query: str, limit: int = 5) -> List[Dict]:
    """Retrieve relevant memories from Mind."""
    return get_mind_bridge().retrieve_relevant(query, limit)
