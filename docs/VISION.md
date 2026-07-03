## Vision — Personalised AI Piano Teacher

North Star: Build a reliable, local-first piano tutor that connects to a Yamaha CVP-301/CVP-391 via USB-MIDI, listens to what you play, diagnoses musical mistakes, and generates short, personalised practice plans that help you improve.

Key principles:
- Local-first and low-latency: MIDI I/O must be real-time and reliable on a laptop.
- Honest feedback: diagnostics must be specific, actionable, and data-driven.
- Play-first UX: the interface should make playing easy — large keyboard or Synthesia-style lane view.
- Progressive complexity: start with deterministic rule-based diagnosis, enable LLM coaching only as an optional add-on.

Primary outcomes:
- Press keys → immediate response in the app (visual + scoring).
- Load a MIDI → the app can present it in a tutor mode and guide the student.
- After a short session, receive 2–3 targeted drills and a short practice plan.

This doc set contains the full original spec and a roadmap to build the product iteratively.
