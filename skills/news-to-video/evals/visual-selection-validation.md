# Visual selection validation — 2026-10-31

34 offline tests passed: 8 scoring, 10 image adapter, 9 presenter, 7 visual beats.

Command: runtime Python -m unittest test_visual_selection test_generated_images test_presenter test_visual_beats (scripts directory).

New score tests cover weighted calculation, hard-gate precedence, missing image alternative, override explanation, near-tie picture preference, legacy mode, NaN/bool rejection and invalid host exemption.

Weights and five-point preference margin are initial editorial policy, not empirically calibrated audience predictions. No live image generation, full video rerender or independent model benchmark performed for this skill change. Existing delivered video is unchanged.
