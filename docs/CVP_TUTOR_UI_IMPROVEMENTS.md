# CVP Tutor UI And UX Improvement Backlog

This document consolidates every improvement suggestion raised so far for `cvp_tutor`, especially around interface design, usability, visual polish, tutor feedback, progression, and workflow.

## Numbered Improvement List

1. Restructure the app into a proper workspace instead of one long stacked form.
2. Use a left control pane and a large right practice pane.
3. Keep the practice area visually dominant over setup and configuration controls.
4. Move utility panels like status, timer, and XP into a grouped lower info row.
5. Make the controls column scroll instead of compressing all controls vertically.
6. Turn the `Song` section into collapsible subsections such as `File`, `Playback`, `Tutor`, and `Track Mixer`.
7. Move `View` toggles into a top toolbar or menu instead of dedicating a full content section to them.
8. Save visible-panel layout preferences between sessions.
9. Improve spacing, padding, and visual hierarchy throughout the app.
10. Make the interface feel less like default Qt widgets and more like a cohesive product.
11. Create a stronger visual design language so features feel intentionally unified rather than incrementally added.
12. Give the right practice pane stronger visual hierarchy so the keyboard, timer, and current cue feel central.
13. Reduce empty or dead-looking panel areas when no file is loaded.
14. Rebuild the keyboard so it visually reads like a real piano keyboard.
15. Improve the proportion of white and black keys.
16. Add subtle depth, shading, highlights, borders, and shadows to the keyboard.
17. Make the black keys feel layered above the white keys.
18. Keep cue visuals as overlays rather than flattening key colors.
19. Make the 2-black and 3-black grouping read more naturally.
20. Add landmarks like middle C or octave markers.
21. Improve keyboard resizing behavior so it keeps believable geometry at different window sizes.
22. Show immediate XP rather than awarding all XP only at the end of a run.
23. Add a proper XP grind bar.
24. Animate the XP bar when it fills.
25. Flash the XP bar on level-up.
26. Add floating `+XP` popups near the progress bar.
27. Add a `Level Up!` banner or celebration state.
28. Show a live song timer.
29. Show a countdown to the next cue.
30. Add a moving marker on the piano roll that tracks song position.
31. Show an upcoming-note warning before the active blue cue.
32. Extend the preview system to show the next 2 to 3 notes as ghost markers for phrase anticipation.
33. Make tutor feedback more visual and less dependent on text labels.
34. Award note XP instantly, then apply timing bonuses after scoring.
35. Keep accompaniment timing consistent during tutor waits.
36. Prevent accompaniment notes from bunching up after a pause.
37. Ensure tutor cues still work even if the learning track is muted.
38. Allow accompaniment to continue with a click or held pad while only learning-hand notes wait, instead of fully pausing everything.
39. Add per-track mute and solo controls for each MIDI file.
40. Add quick mixer actions such as `Mute All`.
41. Add quick mixer actions such as `Unmute All`.
42. Add quick mixer actions such as `Clear Solo`.
43. Add quick mixer actions such as `Solo Learning Part`.
44. Persist track mute and solo preferences per MIDI file.
45. Save those track preferences as part of a broader app profile in the future.
46. Use D&D and 5e-inspired progression to improve motivation.
47. Award XP for correct notes.
48. Treat songs as encounter-like practice experiences.
49. Map musical practice areas to stat and skill-style systems.
50. Add class-style specializations.
51. Add loot and relic-style rewards.
52. Persist XP and profile progress across sessions.
53. Build a full long-term progression system with save data.
54. Add class identity after note XP is stable.
55. Create a one-click `open_cvp_tutor.ps1` launcher.
56. Create a one-click `run_tests.ps1` script.
57. Persist XP between sessions.
58. Add more celebratory progression feedback.
59. Add a moving piano-roll playhead.
60. Add multi-note preview cues.
61. Save UI layout preferences.
62. Polish the layout into a more professional desktop music app.
63. Refactor the layout and styling toward an 85/100 quality level.
64. Do a second-pass redesign with better workflow grouping and stronger visual focus.
65. Make the app feel less like a prototype tool and more like a polished music product.
66. Make the current practice state the visual center of gravity.
67. Make first-time use easier by clarifying what the user should do first.
68. Make the app more emotionally rewarding, not just functionally capable.

## Suggested Prioritisation

If this list is tackled in phases, the best sequence is:

1. Fix clarity and usability first.
2. Improve the keyboard and cue visuals second.
3. Strengthen the tutor and feedback loop third.
4. Expand persistence and progression fourth.
5. Do full visual polish and workflow refinement last.

## Best Immediate Next Steps

The highest-value next steps from this backlog are:

1. Rebuild the keyboard visuals so it looks like a real piano.
2. Turn the `Song` area into collapsible grouped sections.
3. Add a moving piano-roll playhead.
4. Persist panel visibility and layout preferences.
5. Add more visible cue and reward feedback such as `+XP` popups and a `Level Up!` banner.
