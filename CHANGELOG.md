# Changelog

## 0.1.0 (2026-10-14)

The first release.

- **The AR-15 family:** one platform with five presets (M4A1, M16A2, AR15, M4A1_Kitted, AR15_Optic). Any parameter
  can change: barrel length, gas system, handguard, sights, flattop or carry handle, stock and its position, magazine,
  muzzle device, grip and its texture, the selector's marks, the finishes, the scale.
- **A rigged gun:** one bone a moving part (Bolt, ChargingHandle, DustCover, BoltCatch, MagRelease, Selector, Trigger,
  ForwardAssist, Magazine, MagRound, Stock), each with its real pivot and travel. FBX out, with the hand magazine on
  its own and one FBX an attachment.
- **Self-checks on every build:** lengths against published figures, the chamber on the bore, the dust cover over the
  port and open against the lower, the magazine in its well, the bolt's travel, the sight line, each attachment on its
  rail and clear, the optics on the iron sight line, and every visible part with its features (`parts_complete`).
- **The real-gun check:** `compare_to_reference` draws a build's side outline at a reference photo's scale and
  names the parts where it differs. It ships with one reference, a public domain photo of an M4A1.
- **Attachments on sockets:** nine classes on Picatinny and M-LOK slots, each its own FBX: folding backup sights, the
  M4 carry handle, a red dot, a holographic sight, a 3x flip magnifier, a 4x prism sight, a vertical grip, a light.
- **Motion and clips:** the cycle as an action in every `.blend`, GIFs of it on request, and the gun's own clips
  (charge, chamber check, fire, last shot, reload, empty reload, stock) keyed from real timings and measured.
