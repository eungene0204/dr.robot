# Additional original game benchmark evidence

Accessed **2026-11-11**. Six additional games, **16 exact average-FPS observations**. All sources below are ComputerBase's own experiments, not FPS prediction sites. Source publication years remain 2023–2025; viewing an old measurement today does not make it a measurement of the current patch. Unknown build, rendering, frame-generation or other details stay unknown. Do not convert these results into another PC's guaranteed FPS.

## Popularity selection evidence

The primary [Steam Most Played chart](https://store.steampowered.com/charts/mostplayed), viewed on the access date, includes Dota 2, Rust, Rainbow Six Siege, Warframe, Dead by Daylight, Baldur's Gate 3, GTA V Enhanced, Helldivers 2, Red Dead Redemption 2, Destiny 2, Palworld, Elden Ring, MapleStory and Path of Exile 2. This supports including these established PC titles; it does not mean the expansion is exactly Steam's top 20 or that Steam covers Korean launcher-only audiences. Rankings and player counts change continuously. Minecraft/Genshin/Korean launcher games require their own official platform evidence, not extrapolated Steam counts.

## Verified source contexts and exclusions

- **Baldur's Gate 3:** [original methodology and charts](https://www.computerbase.de/artikel/gaming/baldurs-gate-3-benchmark-test.85071/seite-3), [original feature table](https://www.computerbase.de/artikel/gaming/baldurs-gate-3-benchmark-test.85071/). RTX4060 averages 70.0 at1080p and52.8 at1440p, Ultra/Vulkan, Ryzen7950X3D/32GB. The table does not explicitly give an upscaling toggle, so it remains unknown and these records are not selection eligible. At publication the game had no FG or RT. The measured first-act scene cannot represent later acts' CPU demands.
- **Helldivers 2:** [original native and reduced-setting charts plus methodology](https://www.computerbase.de/artikel/gaming/helldivers-2-benchmark-test.87973/). At1080p Ultra/native, RTX4060=78.9 and4060Ti8GB=94.5; at1440p=55.9/69.0. Native runs disable Async Compute; FG is unconfirmed. Training scenes are reproducible but the author warns real generated missions may run10–15% slower. A separate High+UltraQuality spatial-upscaled4060 result113.1 is not native. No mission guarantee or universal training→mission conversion is created.
- **Palworld:** [original charts and methodology](https://www.computerbase.de/artikel/gaming/palworld-early-access-benchmark-test.88052/).1080p maximum:4060=81.6,4060Ti8GB=101.3. Medium:4060=118.1. All use TSR, whose internal resolution is not specified; these must not become native1080p evidence. FG is unconfirmed.
- **Diablo IV/Vessel of Hatred:** [original charts and methodology](https://www.computerbase.de/artikel/gaming/diablo-4-vessel-of-hatred-benchmark-test.89926/seite-2).1080p DLAA raster4060=89.6, but the chart explicitly flags reduced texture quality. This is stored as quality-degraded and excluded from candidate selection, not advertised as intact Ultra fidelity. FG setting is unconfirmed. The scene is from the DLC, not every base-game/dungeon scenario.
- **Black Myth Wukong:** [RTX5060 review method/settings](https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/), [original charts](https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/seite-3).1080p Cinematic/DLSSQuality, noFG/fullRT:4060=26.5,5060=31.7,5060Ti8GB=37.2,5060Ti16GB=38.7. These upscaled averages are not native. The method's RAM-speed prose/table disagree(6200/6000), retained in metadata rather than resolved silently.
- **Monster Hunter Wilds:** [original charts and methodology](https://www.computerbase.de/artikel/gaming/monster-hunter-wilds-benchmark-test.91864/seite-2).RTX4060=35.8 at1440p Ultra/DLSSQuality/noRT, Frame-generation and per-run texture-DLC state are not explicit. The source warns about8GB texture/VRAM limits with the DLC. It must not be applied to native1080p or current optimized patches.

## Integration constraints

Only the Helldivers2 native contexts are marked `selection_eligible=true` as GPU-level advisory evidence; they still have unknownFG status and a training-scene caveat. Every other context is deliberately retained for transparent coverage display only. Do not ignore `quality_degraded` or `selection_eligible`; never use all records with a matching game name as equivalent conditions. Exact GPU+VRAM variants, output resolution, preset, upscaling and FG/RT state must remain attached to each row. All rows are averages; this seed does not relabel or include percentile measurements as averages.

```json
{
  "schema_version": 1,
  "accessed_at": "2026-11-11",
  "benchmarks": [
    {
      "source": {
        "id": "computerbase-bg3-2023-08-09",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2023-08-09",
        "methodology_url": "https://www.computerbase.de/artikel/gaming/baldurs-gate-3-benchmark-test.85071/seite-3"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 9 7950X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 32,
        "memory": "DDR5-6000 CL30-38-38-96",
        "os": "Windows 11 22H2",
        "runs": null,
        "aggregation": null,
        "driver_version": "GeForce 536.67",
        "measurement_date": null
      },
      "contexts": {
        "bg3-fhd-ultra-vulkan": {
          "game": "baldurs_gate_3",
          "results_url": "https://www.computerbase.de/artikel/gaming/baldurs-gate-3-benchmark-test.85071/seite-3",
          "resolution": [
            1920,
            1080
          ],
          "preset": "ultra",
          "api": "Vulkan",
          "upscaling": null,
          "frame_generation": false,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "15-second route at Trielta Crags outside the first act main map",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "upscaling_disabled_not_explicit_in_table"
          ]
        },
        "bg3-qhd-ultra-vulkan": {
          "game": "baldurs_gate_3",
          "results_url": "https://www.computerbase.de/artikel/gaming/baldurs-gate-3-benchmark-test.85071/seite-3",
          "resolution": [
            2560,
            1440
          ],
          "preset": "ultra",
          "api": "Vulkan",
          "upscaling": null,
          "frame_generation": false,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "15-second route at Trielta Crags outside the first act main map",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "upscaling_disabled_not_explicit_in_table"
          ]
        }
      },
      "observations": [
        {
          "id": "cb-20230809-bg3-4060-fhd",
          "context": "bg3-fhd-ultra-vulkan",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 70.0
        },
        {
          "id": "cb-20230809-bg3-4060-qhd",
          "context": "bg3-qhd-ultra-vulkan",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 52.8
        }
      ],
      "fps_guarantee": false
    },
    {
      "source": {
        "id": "computerbase-hd2-2024-05-03",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2024-05-03",
        "methodology_url": "https://www.computerbase.de/artikel/gaming/helldivers-2-benchmark-test.87973/"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 9 7950X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 48,
        "memory": "DDR5-6000 CL36-36-36-72",
        "os": "Windows 11 23H2",
        "runs": null,
        "aggregation": null,
        "driver_version": "GeForce 552.22",
        "measurement_date": null
      },
      "contexts": {
        "hd2-fhd-ultra-native": {
          "game": "helldivers_2",
          "results_url": "https://www.computerbase.de/artikel/gaming/helldivers-2-benchmark-test.87973/",
          "resolution": [
            1920,
            1080
          ],
          "preset": "ultra",
          "api": null,
          "upscaling": false,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "Hand-authored training mission; actual generated missions may be 10-15% slower per reviewer",
          "selection_eligible": true,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "exact_route",
            "api"
          ],
          "async_compute": false
        },
        "hd2-qhd-ultra-native": {
          "game": "helldivers_2",
          "results_url": "https://www.computerbase.de/artikel/gaming/helldivers-2-benchmark-test.87973/",
          "resolution": [
            2560,
            1440
          ],
          "preset": "ultra",
          "api": null,
          "upscaling": false,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "Hand-authored training mission; actual generated missions may be 10-15% slower per reviewer",
          "selection_eligible": true,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "exact_route",
            "api"
          ],
          "async_compute": false
        },
        "hd2-fhd-high-ultraquality": {
          "game": "helldivers_2",
          "results_url": "https://www.computerbase.de/artikel/gaming/helldivers-2-benchmark-test.87973/",
          "resolution": [
            1920,
            1080
          ],
          "preset": "high",
          "api": null,
          "upscaling": true,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "Training mission",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "exact_route",
            "api",
            "internal_render_resolution"
          ],
          "upscaler": "game_spatial_upscaler",
          "upscaling_mode": "ultra_quality",
          "async_compute": false
        }
      },
      "observations": [
        {
          "id": "cb-20240503-hd2-4060-fhd",
          "context": "hd2-fhd-ultra-native",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 78.9
        },
        {
          "id": "cb-20240503-hd2-4060ti8-fhd",
          "context": "hd2-fhd-ultra-native",
          "gpu": "GeForce RTX 4060 Ti",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 94.5
        },
        {
          "id": "cb-20240503-hd2-4060-qhd",
          "context": "hd2-qhd-ultra-native",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 55.9
        },
        {
          "id": "cb-20240503-hd2-4060ti8-qhd",
          "context": "hd2-qhd-ultra-native",
          "gpu": "GeForce RTX 4060 Ti",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 69.0
        },
        {
          "id": "cb-20240503-hd2-4060-fhd-high-upscaled",
          "context": "hd2-fhd-high-ultraquality",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 113.1
        }
      ],
      "fps_guarantee": false
    },
    {
      "source": {
        "id": "computerbase-palworld-2024-05-13",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2024-05-13",
        "methodology_url": "https://www.computerbase.de/artikel/gaming/palworld-early-access-benchmark-test.88052/"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 9 7950X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 48,
        "memory": "DDR5-6000 CL36-36-36-72",
        "os": "Windows 11 23H2",
        "runs": null,
        "aggregation": null,
        "driver_version": "GeForce 552.22",
        "measurement_date": null
      },
      "contexts": {
        "palworld-fhd-max-tsr": {
          "game": "palworld",
          "results_url": "https://www.computerbase.de/artikel/gaming/palworld-early-access-benchmark-test.88052/",
          "resolution": [
            1920,
            1080
          ],
          "preset": "maximum",
          "api": "DirectX 11",
          "upscaling": true,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "Outdoor open-world area near the beginning, long view distance and substantial vegetation",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "internal_render_resolution"
          ],
          "upscaler": "TSR",
          "upscaling_mode": null
        },
        "palworld-fhd-medium-tsr": {
          "game": "palworld",
          "results_url": "https://www.computerbase.de/artikel/gaming/palworld-early-access-benchmark-test.88052/",
          "resolution": [
            1920,
            1080
          ],
          "preset": "medium",
          "api": "DirectX 11",
          "upscaling": true,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "Outdoor open-world area near the beginning, long view distance and substantial vegetation",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "internal_render_resolution"
          ],
          "upscaler": "TSR",
          "upscaling_mode": null
        }
      },
      "observations": [
        {
          "id": "cb-20240513-palworld-4060-fhd-max-tsr",
          "context": "palworld-fhd-max-tsr",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 81.6
        },
        {
          "id": "cb-20240513-palworld-4060ti8-fhd-max-tsr",
          "context": "palworld-fhd-max-tsr",
          "gpu": "GeForce RTX 4060 Ti",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 101.3
        },
        {
          "id": "cb-20240513-palworld-4060-fhd-medium-tsr",
          "context": "palworld-fhd-medium-tsr",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 118.1
        }
      ],
      "fps_guarantee": false
    },
    {
      "source": {
        "id": "computerbase-diablo4-voh-2024-10-12",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2024-10-12",
        "methodology_url": "https://www.computerbase.de/artikel/gaming/diablo-4-vessel-of-hatred-benchmark-test.89926/seite-2"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 9 7950X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 48,
        "memory": "DDR5-6000 CL36-36-36-72",
        "os": "Windows 11 23H2",
        "runs": null,
        "aggregation": null,
        "driver_version": "GeForce 565.90",
        "measurement_date": null
      },
      "contexts": {
        "diablo4-voh-fhd-ultra-dlaa-reduced-texture": {
          "game": "diablo_iv",
          "results_url": "https://www.computerbase.de/artikel/gaming/diablo-4-vessel-of-hatred-benchmark-test.89926/seite-2",
          "resolution": [
            1920,
            1080
          ],
          "preset": "ultra_with_automatic_reduced_texture_quality",
          "api": "DirectX 12",
          "upscaling": false,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "20-second walk in new jungle near the beginning of Vessel of Hatred, quest Ein blutiger Pfad",
          "selection_eligible": false,
          "quality_degraded": true,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "actual_texture_level_after_fallback"
          ],
          "anti_aliasing": "DLAA",
          "edition": "Vessel of Hatred campaign",
          "quality_warning": "Original RTX 4060 chart explicitly reports reduced texture quality; not equivalent to full Ultra texture fidelity"
        }
      },
      "observations": [
        {
          "id": "cb-20241012-diablo4-4060-fhd-dlaa-reduced-texture",
          "context": "diablo4-voh-fhd-ultra-dlaa-reduced-texture",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 89.6
        }
      ],
      "fps_guarantee": false
    },
    {
      "source": {
        "id": "computerbase-rtx5060-review-2025-06-02",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2025-06-02",
        "methodology_url": "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 7 9800X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 48,
        "memory": "DDR5 CL30-38-38-96; prose says 6200 MT/s, table says 6000 MT/s",
        "os": "Windows 11 24H2",
        "runs": null,
        "aggregation": null,
        "driver_version": null,
        "measurement_date": null,
        "driver_versions_by_gpu": {
          "GeForce RTX 4060": "GeForce 566.14 baseline, some games retested if changed",
          "GeForce RTX 5060": "GeForce 576.52",
          "GeForce RTX 5060 Ti": "GeForce 575.94"
        }
      },
      "contexts": {
        "wukong-fhd-cinematic-dlss-quality": {
          "game": "black_myth_wukong",
          "results_url": "https://www.computerbase.de/artikel/grafikkarten/nvidia-geforce-rtx-5060-test.92811/seite-3",
          "resolution": [
            1920,
            1080
          ],
          "preset": "cinematic",
          "api": null,
          "upscaling": true,
          "frame_generation": false,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": null,
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "exact_scene",
            "api",
            "memory_clock_conflict"
          ],
          "upscaler": "DLSS",
          "upscaling_mode": "quality"
        }
      },
      "observations": [
        {
          "id": "cb-20250602-wukong-4060-fhd-dlssq",
          "context": "wukong-fhd-cinematic-dlss-quality",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 26.5
        },
        {
          "id": "cb-20250602-wukong-5060-fhd-dlssq",
          "context": "wukong-fhd-cinematic-dlss-quality",
          "gpu": "GeForce RTX 5060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 31.7
        },
        {
          "id": "cb-20250602-wukong-5060ti8-fhd-dlssq",
          "context": "wukong-fhd-cinematic-dlss-quality",
          "gpu": "GeForce RTX 5060 Ti",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 37.2
        },
        {
          "id": "cb-20250602-wukong-5060ti16-fhd-dlssq",
          "context": "wukong-fhd-cinematic-dlss-quality",
          "gpu": "GeForce RTX 5060 Ti",
          "vram_gb": 16,
          "metric": "average_fps",
          "value": 38.7
        }
      ],
      "fps_guarantee": false
    },
    {
      "source": {
        "id": "computerbase-mhwilds-2025-03-31",
        "owner": "ComputerBase / Wolfgang Andermahr",
        "kind": "original_reviewer_measurement",
        "published_at": "2025-03-31",
        "methodology_url": "https://www.computerbase.de/artikel/gaming/monster-hunter-wilds-benchmark-test.91864/seite-2"
      },
      "accessed_at": "2026-11-11",
      "platform": {
        "cpu": "AMD Ryzen 7 9800X3D",
        "motherboard": "ASUS ROG Crosshair X670E Hero",
        "memory_gb": 48,
        "memory": "DDR5-6000 CL30-38-38-96",
        "os": "Windows 11 24H2",
        "runs": null,
        "aggregation": null,
        "driver_version": "GeForce 572.83",
        "measurement_date": null
      },
      "contexts": {
        "mhw-qhd-ultra-dlss-quality": {
          "game": "monster_hunter_wilds",
          "results_url": "https://www.computerbase.de/artikel/gaming/monster-hunter-wilds-benchmark-test.91864/seite-2",
          "resolution": [
            2560,
            1440
          ],
          "preset": "ultra",
          "api": "DirectX 12",
          "upscaling": true,
          "frame_generation": null,
          "ray_tracing": false,
          "path_tracing": false,
          "scene": "20-second forest route near the tent, vegetation and water",
          "selection_eligible": false,
          "quality_degraded": false,
          "unknown_fields": [
            "game_build",
            "measurement_date",
            "frame_generation",
            "texture_dlc_enabled_in_individual_run"
          ],
          "upscaler": "DLSS",
          "upscaling_mode": "quality",
          "texture_dlc": null,
          "quality_warning": "Reviewer warns 8GB can overflow at highest textures with the texture DLC"
        }
      },
      "observations": [
        {
          "id": "cb-20250331-mhw-4060-qhd-dlssq",
          "context": "mhw-qhd-ultra-dlss-quality",
          "gpu": "GeForce RTX 4060",
          "vram_gb": 8,
          "metric": "average_fps",
          "value": 35.8
        }
      ],
      "fps_guarantee": false
    }
  ]
}
```
