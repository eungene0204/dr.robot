# Original measured game benchmark evidence

Accessed 2026-11-11. Four seed observations cover two games and two mainstream desktop GPUs. These are measurements of a complete test system, not guarantees for a GPU installed in another PC. Do not convert Blender scores into game FPS or extrapolate these observations to QHD/4K, other presets, or minimum FPS.

## Source and shared platform

[ComputerBase / DevPandi, generation comparison, 2026-04-30](https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/) owns the original measurements. Its methodology specifies Ryzen 7 9800X3D, ASUS ROG Strix B650E-F, 64 GB G.Skill DDR5-6400 CL32 and Windows 11 24H2. Each scene is measured three times and averaged. The author explicitly states native rendering without upscaling. This is an everyday system with background applications. Exact driver versions, game builds and measurement dates are not specified in the inspected methodology.

## Overwatch 2

[Original results](https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/seite-3) expose exact average values: RTX 4060 8 GB **177.0 FPS**, RTX 5060 8 GB **236.0 FPS**, at 1080p.

The original [video settings image](https://pics.computerbase.de/1/1/8/1/2/3-650a18578c4dea84/23-1280.jpg) shows DX12 beta, 1920×1080, dynamic scaling off, render scale automatic, VSync off and 600 FPS cap. The [quality settings image](https://pics.computerbase.de/1/1/8/1/2/3-650a18578c4dea84/24-1080.f8cb022e.jpg) shows a custom configuration: High textures, SMAA Medium, 16× filtering; Ultra fog, models, shadows, effects and lighting; High refraction, AO and reflections. This must not be relabeled as a standard Ultra preset. Frame generation is not explicitly documented. The text discusses training areas and multiplayer variability but does not identify an exact reproducible route.

## Cyberpunk 2077

[Original results and scene description](https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/seite-2) give RTX 4060 8 GB **61.0 FPS**, RTX 5060 8 GB **91.3 FPS** at 1080p without RT. The scene walks through Dogtown from Mr. Hands' pyramid toward the stadium stairs and neon signs; the author describes it as demanding.

The [resolution image](https://pics.computerbase.de/1/1/8/1/2/3-650a18578c4dea84/3-1080.35ba6b75.jpg) shows 1920×1080. The [main graphics image](https://pics.computerbase.de/1/1/8/1/2/3-650a18578c4dea84/4-1080.fe241002.jpg) explicitly shows custom settings, scaling off, frame generation off, RT/PT off, High textures/crowd. [Advanced settings](https://pics.computerbase.de/1/1/8/1/2/3-650a18578c4dea84/6-1080.239c8450.jpg) mix High shadows/AO with Ultra volumetric fog/clouds/decals/SSR. Consequently this is a custom High/Ultra raster measurement, not a stock Ultra preset.

## Machine-readable seed observations

`selection_scope` permits choosing among observed GPU models for comparable native FHD requests. `fps_guarantee` remains false. A request for a stock named preset, QHD/4K, stable/low FPS, different CPU or stricter competitive scenario needs additional evidence. Missing fields must remain unknown rather than acquire inferred values.

```json
{
  "schema_version": 1,
  "accessed_at": "2026-11-11",
  "source": {
    "id": "computerbase-generation-comparison-2026-04-30",
    "owner": "ComputerBase / DevPandi",
    "kind": "original_reviewer_measurement",
    "published_at": "2026-04-30",
    "methodology_url": "https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/"
  },
  "platform": {
    "cpu": "AMD Ryzen 7 9800X3D",
    "motherboard": "ASUS ROG Strix B650E-F",
    "memory_gb": 64,
    "memory": "DDR5-6400 CL32",
    "os": "Windows 11 24H2",
    "runs": 3,
    "aggregation": "mean_of_three_runs",
    "background_applications": true,
    "driver_version": null,
    "measurement_date": null
  },
  "contexts": {
    "overwatch2-fhd-custom": {
      "game": "overwatch-2",
      "results_url": "https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/seite-3",
      "resolution": [1920, 1080],
      "preset": "custom_high_ultra",
      "api": "DirectX 12 beta",
      "upscaling": false,
      "dynamic_resolution": false,
      "render_scale_ui": "automatic",
      "native_rendering_evidence": "author_methodology",
      "frame_generation": null,
      "ray_tracing": null,
      "scene": null,
      "unknown_fields": ["exact_scene", "game_build", "frame_generation"]
    },
    "cyberpunk2077-fhd-custom-raster": {
      "game": "cyberpunk-2077",
      "results_url": "https://www.computerbase.de/artikel/grafikkarten/grafikkarten-vergleich-radeon-rx-7600-xt-rx-9060-xt-geforce-rtx-4060-rtx-5060-intel-xe-arc-a580-b580-duell.93230/seite-2",
      "resolution": [1920, 1080],
      "preset": "custom_high_ultra",
      "api": null,
      "upscaling": false,
      "frame_generation": false,
      "ray_tracing": false,
      "path_tracing": false,
      "scene": "Dogtown walk from Mr. Hands pyramid toward stadium stairs and neon signs",
      "unknown_fields": ["game_build", "api"]
    }
  },
  "observations": [
    {"id": "cb-20260430-ow2-rtx4060", "context": "overwatch2-fhd-custom", "gpu": "GeForce RTX 4060", "vram_gb": 8, "metric": "average_fps", "value": 177.0},
    {"id": "cb-20260430-ow2-rtx5060", "context": "overwatch2-fhd-custom", "gpu": "GeForce RTX 5060", "vram_gb": 8, "metric": "average_fps", "value": 236.0},
    {"id": "cb-20260430-cp2077-rtx4060", "context": "cyberpunk2077-fhd-custom-raster", "gpu": "GeForce RTX 4060", "vram_gb": 8, "metric": "average_fps", "value": 61.0},
    {"id": "cb-20260430-cp2077-rtx5060", "context": "cyberpunk2077-fhd-custom-raster", "gpu": "GeForce RTX 5060", "vram_gb": 8, "metric": "average_fps", "value": 91.3}
  ],
  "selection_scope": "observed_gpu_models_comparable_native_fhd_custom_settings",
  "fps_guarantee": false,
  "unsupported_inferences": ["QHD_or_4K_FPS", "minimum_or_1_percent_low_FPS", "performance_on_a_different_CPU", "named_stock_preset_equivalence", "unmeasured_GPU_FPS"]
}
```

## Coverage gaps and exclusions

No adequately contextualized original numeric observations for Valorant, CS2 or Fortnite were verified in this pass. Their graph entries should use official requirements with honest missing measured-performance coverage until further original tests are collected. FPS-calculator/forecast sites and secondary summaries were excluded. The ComputerBase charts also expose an unspecified percentile metric; it is intentionally excluded because its definition was not established. No chart bar lengths were estimated.
