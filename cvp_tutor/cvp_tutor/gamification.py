from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from .scoring import ScoreEvent
try:
    from .dnd import DnDManager
except Exception:
    DnDManager = None


@dataclass
class Profile:
    xp: int = 0
    gold: int = 0
    level: int = 1
    total_notes: int = 0
    perfect: int = 0
    good: int = 0
    miss: int = 0
    wrong: int = 0
    best_streak: int = 0


@dataclass
class RewardSummary:
    xp_gained: int
    gold_gained: int
    notes: int
    perfect: int
    good: int
    miss: int
    wrong: int
    best_streak: int


class GamificationManager:
    """Minimal XP/gold tracker for DnD-style progression."""

    def __init__(self, profile_path: Path) -> None:
        self.profile_path = profile_path
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile = self._load()
        # optional extended DnD manager (scaffold)
        try:
            if DnDManager is not None:
                self.dnd = DnDManager(profile_path.parent / "dnd_profile.json")
            else:
                self.dnd = None
        except Exception:
            self.dnd = None

    def _load(self) -> Profile:
        if self.profile_path.exists():
            try:
                data = json.loads(self.profile_path.read_text())
                return Profile(**data)
            except Exception:
                # Start fresh if the profile is corrupt
                return Profile()
        return Profile()

    def _save(self) -> None:
        self.profile_path.write_text(json.dumps(asdict(self.profile), indent=2))

    def _level_from_xp(self, xp: int) -> tuple[int, int]:
        """Return (level, xp_into_level). Flat 500 XP per level for now."""
        level = xp // 500 + 1
        xp_into = xp % 500
        return level, xp_into

    def apply_score(self, score_events: List[ScoreEvent]) -> RewardSummary:
        xp = 0
        gold = 0
        perfect = 0
        good = 0
        miss = 0
        wrong = 0
        streak = 0
        best_streak = self.profile.best_streak
        notes = 0

        for event in score_events:
            notes += len(event.expected)
            if event.verdict == "PERFECT":
                xp += 10
                gold += 2
                perfect += 1
                streak += 1
            elif event.verdict == "GOOD":
                xp += 6
                gold += 1
                good += 1
                streak += 1
            elif event.verdict in {"EARLY", "LATE"}:
                xp += 3
                gold += 1
                good += 1
                streak += 1
            elif event.verdict == "WRONG":
                wrong += 1
                streak = 0
            else:
                miss += 1
                streak = 0
            if streak > best_streak:
                best_streak = streak

        self.profile.xp += xp
        self.profile.gold += gold
        self.profile.total_notes += notes
        self.profile.perfect += perfect
        self.profile.good += good
        self.profile.miss += miss
        self.profile.wrong += wrong
        self.profile.best_streak = best_streak

        level, _ = self._level_from_xp(self.profile.xp)
        self.profile.level = level
        self._save()

        return RewardSummary(
            xp_gained=xp,
            gold_gained=gold,
            notes=notes,
            perfect=perfect,
            good=good,
            miss=miss,
            wrong=wrong,
            best_streak=best_streak,
        )

    def hero_text(self, reward: RewardSummary | None = None) -> str:
        level, xp_into = self._level_from_xp(self.profile.xp)
        xp_next = 500
        parts = [
            f"Hero Lv{level}",
            f"XP {xp_into}/{xp_next}",
            f"Gold {self.profile.gold}",
            f"Streak {self.profile.best_streak}",
        ]
        if reward:
            parts.append(f"+{reward.xp_gained} XP / +{reward.gold_gained} Gold")
        return " | ".join(parts)

    def get_progress(self) -> tuple[int, int, int]:
        """Return (level, current_xp, max_xp_for_level)."""
        level, xp_into = self._level_from_xp(self.profile.xp)
        return level, xp_into, 500

    # Convenience wrappers to the extended DnD manager
    def dnd_award_xp(self, amount: int) -> Optional[int]:
        if getattr(self, "dnd", None):
            return self.dnd.award_xp(amount)
        return None

    def dnd_add_gold(self, amount: int) -> None:
        if getattr(self, "dnd", None):
            return self.dnd.add_gold(amount)
        return None

    def check_achievements(self) -> List[dict]:
        """Check for unlockable achievements and return list of unlocked achievements.

        This is a lightweight ruleset; if a `DnDManager` is available we delegate
        persistence to it. Returns a list of dicts with keys `id`, `name`, `description`.
        """
        unlocked: List[dict] = []
        candidates = [
            ("century_perfects", "Century of Perfects", "Get 100 PERFECT notes"),
            ("unstoppable_streak", "Unstoppable", "Achieve a streak of 50"),
            ("veteran", "Veteran", "Reach level 10"),
            ("note_mill", "Note Mill", "Record 1000 total notes"),
        ]

        for aid, name, desc in candidates:
            try:
                should_unlock = False
                if aid == "century_perfects" and self.profile.perfect >= 100:
                    should_unlock = True
                if aid == "unstoppable_streak" and self.profile.best_streak >= 50:
                    should_unlock = True
                if aid == "veteran" and self.profile.level >= 10:
                    should_unlock = True
                if aid == "note_mill" and self.profile.total_notes >= 1000:
                    should_unlock = True

                if should_unlock:
                    # Delegate persistence to DnDManager if present
                    if getattr(self, "dnd", None):
                        ok = self.dnd.unlock_achievement(aid, name, desc)
                        if ok:
                            unlocked.append({"id": aid, "name": name, "description": desc})
                    else:
                        # If no DnDManager, write a simple achievements file
                        ach_file = self.profile_path.parent / "achievements.json"
                        existing = []
                        if ach_file.exists():
                            try:
                                existing = json.loads(ach_file.read_text())
                            except Exception:
                                existing = []
                        if not any(a.get("id") == aid for a in existing):
                            existing.append({"id": aid, "name": name, "description": desc, "unlocked_at": __import__("datetime").datetime.utcnow().isoformat()})
                            try:
                                ach_file.write_text(json.dumps(existing, indent=2))
                                unlocked.append({"id": aid, "name": name, "description": desc})
                            except Exception:
                                pass
            except Exception:
                continue
        return unlocked
