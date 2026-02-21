#!/usr/bin/env python3
"""
NicheNet - Niche Intelligence Network for X/Twitter.

Maps accounts in our niche, tracks relationships, identifies
conversation hubs, and generates engagement opportunities.

"Know your niche. Know your people. Engage genuinely."
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    from lib.x_voice import get_x_voice
except ImportError:
    get_x_voice = None


# State directory
NICHE_DIR = Path.home() / ".spark" / "niche_intel"
ACCOUNTS_FILE = NICHE_DIR / "tracked_accounts.json"
HUBS_FILE = NICHE_DIR / "hubs.json"
OPPORTUNITIES_FILE = NICHE_DIR / "opportunities.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TrackedAccount:
    """An account tracked in our niche."""

    handle: str
    topics: List[str] = field(default_factory=list)
    relevance: float = 0.5  # 0-1 how relevant to our niche
    warmth: str = "cold"  # cold | cool | warm | hot | ally
    interaction_count: int = 0
    they_initiated_count: int = 0
    we_initiated_count: int = 0
    last_interaction: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    discovered_via: str = ""  # How we found them
    notes: str = ""


@dataclass
class ConversationHub:
    """A detected conversation hub."""

    hub_id: str
    hub_type: str  # topic | account | thread
    description: str
    engagement_level: float = 0.0  # 0-10
    key_accounts: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    times_observed: int = 1


@dataclass
class EngagementOpportunity:
    """A strategic engagement opportunity."""

    target: str  # Account handle or thread ID
    reason: str
    urgency: int = 3  # 1-5
    suggested_tone: str = "conversational"
    suggested_hook: str = "observation"
    expires_at: float = 0  # Unix timestamp, 0 = no expiry
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acted_on: bool = False


# ---------------------------------------------------------------------------
# Core NicheMapper
# ---------------------------------------------------------------------------


class NicheMapper:
    """Maps and tracks relationships within Spark's niche on X.

    Key capabilities:
    - Discover and track accounts in the niche
    - Track warmth progression with each account
    - Identify conversation hubs (topic clusters, key threads)
    - Generate strategic engagement opportunities
    - Integrate with XVoice for warmth-aware tone selection
    """

    MAX_TRACKED = 500
    MAX_HUBS = 50
    MAX_OPPORTUNITIES = 100
    OPPORTUNITY_EXPIRY_HOURS = 48

    def __init__(self):
        self.accounts: Dict[str, TrackedAccount] = {}
        self.hubs: Dict[str, ConversationHub] = {}
        self.opportunities: List[EngagementOpportunity] = []
        self.x_voice = get_x_voice() if callable(get_x_voice) else None
        self._load()

    def _load(self):
        """Load state from disk."""
        if ACCOUNTS_FILE.exists():
            try:
                raw = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
                for h, data in raw.items():
                    self.accounts[h] = TrackedAccount(**data)
            except Exception:
                pass

        if HUBS_FILE.exists():
            try:
                raw = json.loads(HUBS_FILE.read_text(encoding="utf-8"))
                for hid, data in raw.items():
                    self.hubs[hid] = ConversationHub(**data)
            except Exception:
                pass

        if OPPORTUNITIES_FILE.exists():
            try:
                raw = json.loads(OPPORTUNITIES_FILE.read_text(encoding="utf-8"))
                self.opportunities = [EngagementOpportunity(**o) for o in raw]
            except Exception:
                pass

    def _save(self):
        """Persist state."""
        NICHE_DIR.mkdir(parents=True, exist_ok=True)
        ACCOUNTS_FILE.write_text(
            json.dumps({h: asdict(a) for h, a in self.accounts.items()}, indent=2),
            encoding="utf-8",
        )
        HUBS_FILE.write_text(
            json.dumps({h: asdict(hub) for h, hub in self.hubs.items()}, indent=2),
            encoding="utf-8",
        )
        OPPORTUNITIES_FILE.write_text(
            json.dumps([asdict(o) for o in self.opportunities], indent=2),
            encoding="utf-8",
        )

    # ------ Account Discovery ------

    def discover_account(
        self,
        handle: str,
        topics: Optional[List[str]] = None,
        relevance: float = 0.5,
        discovered_via: str = "",
    ) -> TrackedAccount:
        """Discover and begin tracking a new account.

        Args:
            handle: X handle (without @)
            topics: Topics they engage with
            relevance: How relevant to our niche (0-1)
            discovered_via: How we found them

        Returns:
            The TrackedAccount
        """
        handle = handle.lstrip("@").lower()

        if handle in self.accounts:
            # Update existing
            existing = self.accounts[handle]
            if topics:
                new_topics = set(existing.topics) | set(topics)
                existing.topics = list(new_topics)
            existing.relevance = max(existing.relevance, relevance)
            self._save()
            return existing

        account = TrackedAccount(
            handle=handle,
            topics=topics or [],
            relevance=relevance,
            discovered_via=discovered_via,
        )

        # Enforce limit
        if len(self.accounts) >= self.MAX_TRACKED:
            self._prune_least_relevant()

        self.accounts[handle] = account

        # Sync warmth with XVoice
        if self.x_voice is not None and hasattr(self.x_voice, "get_user_warmth"):
            xv_warmth = self.x_voice.get_user_warmth(handle)
            if xv_warmth != "cold":
                account.warmth = xv_warmth

        self._save()
        return account

    def _prune_least_relevant(self):
        """Remove the least relevant, coldest account."""
        if not self.accounts:
            return

        # Sort by relevance and warmth (prefer keeping warm, relevant accounts)
        warmth_order = {"cold": 0, "cool": 1, "warm": 2, "hot": 3, "ally": 4}
        worst = min(
            self.accounts.values(),
            key=lambda a: (warmth_order.get(a.warmth, 0), a.relevance),
        )
        del self.accounts[worst.handle]

    # ------ Relationship Tracking ------

    def update_relationship(
        self,
        handle: str,
        event_type: str,
        they_initiated: bool = False,
    ) -> Optional[Tuple[str, str]]:
        """Update relationship state for an account.

        Args:
            handle: Account handle
            event_type: Type of interaction (reply, like, mention, etc.)
            they_initiated: Whether they initiated

        Returns:
            Tuple of (warmth_before, warmth_after) if warmth changed, else None
        """
        handle = handle.lstrip("@").lower()
        if handle not in self.accounts:
            self.discover_account(handle)

        account = self.accounts[handle]
        warmth_before = account.warmth

        # Update interaction counts
        account.interaction_count += 1
        if they_initiated:
            account.they_initiated_count += 1
        else:
            account.we_initiated_count += 1
        account.last_interaction = datetime.now().isoformat()

        # Delegate warmth transitions to XVoice
        warmth_events = {
            "reply": "reply",
            "reply_received": "reply",
            "like": "mutual_like",
            "mention": "they_mention_us",
            "multi_turn": "multi_turn_convo",
            "share": "share",
            "collab": "collaboration",
            "sustained": "sustained_engagement",
        }
        xv_event = warmth_events.get(event_type, event_type)
        if self.x_voice is not None and hasattr(self.x_voice, "update_warmth"):
            before_warmth = (
                self.x_voice.get_user_warmth(handle)
                if hasattr(self.x_voice, "get_user_warmth")
                else None
            )
            self.x_voice.update_warmth(handle, xv_event)
            # Fall back to original event value when mapped aliases are unsupported.
            if xv_event != event_type and hasattr(self.x_voice, "get_user_warmth"):
                after_warmth = self.x_voice.get_user_warmth(handle)
                if before_warmth == after_warmth:
                    self.x_voice.update_warmth(handle, event_type)

        # Sync warmth from XVoice
        if self.x_voice is not None and hasattr(self.x_voice, "get_user_warmth"):
            account.warmth = self.x_voice.get_user_warmth(handle)

        self._save()

        if account.warmth != warmth_before:
            return (warmth_before, account.warmth)
        return None

    def get_account(self, handle: str) -> Optional[TrackedAccount]:
        """Get a tracked account."""
        return self.accounts.get(handle.lstrip("@").lower())

    def get_accounts_by_warmth(self, warmth: str) -> List[TrackedAccount]:
        """Get all accounts at a specific warmth level."""
        return [a for a in self.accounts.values() if a.warmth == warmth]

    # ------ Hub Identification ------

    def identify_hub(
        self,
        hub_type: str,
        description: str,
        key_accounts: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        engagement_level: float = 5.0,
    ) -> ConversationHub:
        """Identify or update a conversation hub.

        Args:
            hub_type: topic | account | thread
            description: What this hub is about
            key_accounts: Accounts active in this hub
            topics: Topics discussed
            engagement_level: How active (0-10)

        Returns:
            The ConversationHub
        """
        # Generate hub ID from type and description
        hub_id = f"{hub_type}_{description.lower().replace(' ', '_')[:30]}"

        if hub_id in self.hubs:
            hub = self.hubs[hub_id]
            hub.times_observed += 1
            hub.engagement_level = (
                hub.engagement_level * 0.7 + engagement_level * 0.3
            )
            hub.last_active = datetime.now().isoformat()
            if key_accounts:
                existing = set(hub.key_accounts)
                hub.key_accounts = list(existing | set(key_accounts))
        else:
            hub = ConversationHub(
                hub_id=hub_id,
                hub_type=hub_type,
                description=description,
                engagement_level=engagement_level,
                key_accounts=key_accounts or [],
                topics=topics or [],
            )

            if len(self.hubs) >= self.MAX_HUBS:
                # Remove least active hub
                least_active = min(
                    self.hubs.values(), key=lambda h: h.engagement_level
                )
                del self.hubs[least_active.hub_id]

            self.hubs[hub_id] = hub

        self._save()
        return hub

    def get_active_hubs(self, min_engagement: float = 3.0) -> List[ConversationHub]:
        """Get hubs above a minimum engagement level."""
        return sorted(
            [h for h in self.hubs.values() if h.engagement_level >= min_engagement],
            key=lambda h: h.engagement_level,
            reverse=True,
        )

    # ------ Engagement Opportunities ------

    def generate_opportunity(
        self,
        target: str,
        reason: str,
        urgency: int = 3,
        suggested_tone: str = "conversational",
        suggested_hook: str = "observation",
        expires_hours: float = 0,
    ) -> EngagementOpportunity:
        """Generate a strategic engagement opportunity.

        Args:
            target: Who to engage with (handle or thread ID)
            reason: Why this is an opportunity
            urgency: 1-5 urgency
            suggested_tone: Recommended tone
            suggested_hook: Recommended hook type
            expires_hours: Hours until this expires (0 = no expiry)

        Returns:
            The EngagementOpportunity
        """
        expires_at = 0.0
        if expires_hours > 0:
            expires_at = time.time() + (expires_hours * 3600)

        opp = EngagementOpportunity(
            target=target.lstrip("@").lower(),
            reason=reason,
            urgency=min(5, max(1, urgency)),
            suggested_tone=suggested_tone,
            suggested_hook=suggested_hook,
            expires_at=expires_at,
        )

        # Enforce limit
        if len(self.opportunities) >= self.MAX_OPPORTUNITIES:
            # Remove oldest acted-on or expired
            self._cleanup_opportunities()

        self.opportunities.append(opp)
        self._save()
        return opp

    def get_active_opportunities(
        self, min_urgency: int = 1
    ) -> List[EngagementOpportunity]:
        """Get active (unexpired, unacted) opportunities.

        Args:
            min_urgency: Minimum urgency filter (1-5)

        Returns:
            List of active opportunities, sorted by urgency
        """
        now = time.time()
        active = []
        for opp in self.opportunities:
            if opp.acted_on:
                continue
            if opp.expires_at > 0 and opp.expires_at < now:
                continue
            if opp.urgency >= min_urgency:
                active.append(opp)

        return sorted(active, key=lambda o: o.urgency, reverse=True)

    def act_on_opportunity(self, target: str) -> bool:
        """Mark an opportunity as acted on.

        Args:
            target: The target handle/ID

        Returns:
            True if opportunity was found and marked
        """
        target = target.lstrip("@").lower()
        for opp in self.opportunities:
            if opp.target == target and not opp.acted_on:
                opp.acted_on = True
                self._save()
                return True
        return False

    def _cleanup_opportunities(self):
        """Remove expired and old acted-on opportunities."""
        now = time.time()
        self.opportunities = [
            o
            for o in self.opportunities
            if not (
                o.acted_on
                or (o.expires_at > 0 and o.expires_at < now)
            )
        ][-self.MAX_OPPORTUNITIES:]

    # ------ Network Stats ------

    def get_network_stats(self) -> Dict[str, Any]:
        """Get comprehensive network statistics."""
        warmth_dist: Dict[str, int] = {}
        for a in self.accounts.values():
            warmth_dist[a.warmth] = warmth_dist.get(a.warmth, 0) + 1

        topic_counts: Dict[str, int] = {}
        for a in self.accounts.values():
            for t in a.topics:
                topic_counts[t] = topic_counts.get(t, 0) + 1

        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        active_opps = self.get_active_opportunities()

        return {
            "tracked_accounts": len(self.accounts),
            "warmth_distribution": warmth_dist,
            "active_hubs": len(self.get_active_hubs()),
            "total_hubs": len(self.hubs),
            "active_opportunities": len(active_opps),
            "total_opportunities": len(self.opportunities),
            "top_topics": dict(top_topics),
            "total_interactions": sum(
                a.interaction_count for a in self.accounts.values()
            ),
            "reciprocity_rate": self._calculate_reciprocity(),
        }

    def _calculate_reciprocity(self) -> float:
        """Calculate overall reciprocity rate."""
        total_they = sum(a.they_initiated_count for a in self.accounts.values())
        total_we = sum(a.we_initiated_count for a in self.accounts.values())
        total = total_they + total_we
        if total == 0:
            return 0.0
        return round(total_they / total, 2)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_mapper: Optional[NicheMapper] = None


def get_niche_mapper() -> NicheMapper:
    """Get the singleton NicheMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = NicheMapper()
    return _mapper
