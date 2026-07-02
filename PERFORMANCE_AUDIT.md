# Performance Audit Report

## Critical Issues Found

### 1. **State Thrashing in `useGameLoop.ts` (CRITICAL)**

**Location:** `hooks/useGameLoop.ts` lines 105-146

**Problem:** 
- The `useEffect` that depends on `currentTime` runs on EVERY frame (60fps = 60 times per second)
- Inside this effect, it calls `currentSong.forEach()` which iterates through ALL notes
- For each missed note, it calls `setScore()` and `setFeedbackMessage()` - potentially multiple times per frame
- This causes React to re-render hundreds of times per second

**Impact:** Main thread blocked, UI freezes, "Not Responding" errors

**Fix:** Batch state updates, use refs for non-UI state, throttle updates

---

### 2. **Synchronous MIDI Parsing (HIGH)**

**Location:** `frontend/src/pages/page.tsx` line 28

**Problem:**
- `parseMidiFile(buffer)` is called synchronously on the main thread
- Large MIDI files can take seconds to parse, blocking the UI completely

**Impact:** App freezes during file load, no feedback to user

**Fix:** Move parsing to Web Worker or use async with progress indicators

---

### 3. **Render Loop Filtering (MEDIUM)**

**Location:** `components/PianoRoll.tsx` (implied in render logic)

**Problem:**
- Filtering `targetNotes` array happens on every render frame
- No memoization of filtered results

**Impact:** Unnecessary computation on every frame, CPU waste

**Fix:** Memoize filtered notes, only recalculate when `currentTime` changes significantly

---

### 4. **Missing Hook Implementation**

**Location:** `frontend/src/pages/page.tsx` line 21

**Problem:**
- Imports `useGameLoop` from `../hooks/useGameLoop` but the hook signature doesn't match
- The hook expects `(currentSong, liveMidiInput, currentTime, waitModeEnabled)` but page.tsx calls it as `useGameLoop()` with no args

**Impact:** Runtime errors, undefined behavior

**Fix:** Create proper hook implementation or fix imports

---

## Refactoring Plan

1. **Refactor `useGameLoop` to use refs and batched updates**
2. **Move MIDI parsing to Web Worker**
3. **Memoize PianoRoll filtering**
4. **Fix hook implementation mismatch**

