# Game requirements evidence for the recommendation knowledge graph

Accessed: **2026-11-11 (Asia/Seoul)**. Scope: current first-party Windows PC requirement tables for eight games. Steam pages below are publisher-maintained product listings; the publisher identity was verified on each page. These are official requirements, **not measured benchmark results or exact equivalences between old and current components**.

## How to use this evidence

- Preserve `game → profile → hardware alternative` relationships together with source URL and access date. CPU/GPU entries within a list are alternatives, not simultaneous requirements.
- `null` means **not stated by the source**, never zero and never an implicit FHD/60FPS assumption. A commercial default target belongs to a separate policy node with provenance `curated_policy`.
- Official minimums support basic compatibility checks. Official recommended profiles support a baseline and overspending checks; neither alone proves a newer SKU delivers a specific FPS. A `meets_target` edge needs measured game/context evidence, including resolution, preset, render scale/upscaling, ray tracing, CPU and patch.
- VALORANT explicitly publishes 30/60/144FPS tier labels. Store as `official_target`, not `measured_benchmark`; its source omits resolution and preset. League publishes resolution/settings but no FPS. Fortnite publishes an Epic preset but no FPS or resolution.
- Family-only CPUs and GPU series are marked `kind=family`. Do not coerce these to an arbitrary SKU. Hardware IDs are normalized aliases, not proof of equal performance. Per-alternative VRAM takes precedence over a profile-wide value.
- A game name and a high budget do not establish a need for a flagship GPU. Select the least-cost verified sufficient profile; if target evidence is absent, retain uncertainty rather than claim a guaranteed FPS.

## Source catalog and applicability

- **Overwatch** (`overwatch`): [Blizzard Entertainment requirements](https://store.steampowered.com/app/2357570/Overwatch_2/); no requirement-table update date displayed. Windows scope only. CPU families and GPU series have no exact model specified. No resolution, preset, FPS, VRAM or disk type stated. Windows 10 64-bit; DirectX 11.

- **VALORANT** (`valorant`): [Riot Games requirements](https://support.riotgames.com/en-us/valorant/support-tools/minimum-recommended-pc-specs); article updated 2026-05-21. Windows scope only. FPS values are official tier labels, not independently measured benchmarks. Resolution, preset and storage capacity are not specified. SSE4.2 or AVX; DirectX11; Windows11 requires TPM2.0 and UEFI Secure Boot.

- **League of Legends** (`league_of_legends`): [Riot Games requirements](https://support.riotgames.com/en-us/league-of-legends/performance/minimum-and-recommended-system-requirements-league-of-legends); article updated 2026-09-22. Windows scope only. FPS is not specified. Source spells recommended NVIDIA card GeForce 560; normalized GTX560 is a naming interpretation, not a separate performance measurement. SSE4.2 and DirectX11 feature level11_0 required; excludes macOS table.

- **PUBG: BATTLEGROUNDS** (`pubg`): [KRAFTON requirements](https://store.steampowered.com/app/578080/PUBG_BATTLEGROUNDS/); no requirement-table update date displayed. Windows scope only. Per-GPU VRAM is specified; do not replace GTX1060 3GB with6GB silently. Resolution, preset, FPS and disk type not specified. Windows10 64-bit; DirectX11.

- **Counter-Strike 2** (`counter_strike_2`): [Valve requirements](https://store.steampowered.com/app/730/CounterStrike_2/); no requirement-table update date displayed. Windows scope only. Only minimum published; no recommended tier or named Windows GPU model. Do not invent recommended GPU or infer FPS from generic minimum. Resolution, preset and FPS not specified; Windows10.

- **Fortnite** (`fortnite`): [Epic Games requirements](https://www.epicgames.com/help/c-44968506/c-0/a16548002?lang=en-US); no requirement-table update date displayed. Windows scope only. Epic Quality is a distinct preset profile; do not use it for unspecified competitive/Performance Mode requests. No FPS, resolution or free storage capacity published in this support table. Recommended CPUs include mobile U-series parts; no invented desktop conversion.

- **Apex Legends** (`apex_legends`): [Electronic Arts / Respawn requirements](https://store.steampowered.com/app/1172470/Apex_Legends/); no requirement-table update date displayed. Windows scope only. Recommended CPU is family-only, no exact SKU. Current listing DirectX12; older DX11/GT640 sources are not imported. Only HD7790 VRAM2GB explicitly stated; GTX950 VRAM unknown in source. FPS, resolution, preset and disk type unspecified; localized language adds about3.8GB.

- **Cyberpunk 2077** (`cyberpunk_2077`): [CD PROJEKT RED requirements](https://store.steampowered.com/app/1091500/_2077/?curator_clanid=30637343&l=english); no requirement-table update date displayed. Windows scope only. Current Windows listing only; excludes macOS and old pre2.0 requirements. FPS, resolution, preset, ray tracing and upscaling are unspecified in this listing. GTX1060 minimum6GB and RX580 minimum8GB are explicit; other GPU VRAM unspecified. DirectX12; SSD required.

## Machine-readable seed

Fields under each profile are direct factual normalization from that game's linked source, except explicitly disclosed alias normalization. Recommended `Intel Core i5-8250` for League is the current source spelling; it must not silently become the older2021 `i5-3300`. No benchmark scores, GPU ranking, modern replacement SKU or recommended shopping budget was inferred. URLs include a readable Steam Cyberpunk variant because the canonical URL presented an age gate in the research tool.

```json
{
  "schema_version": 1,
  "accessed_at": "2026-11-11",
  "games": [
    {
      "game_id": "overwatch",
      "name": "Overwatch",
      "aliases": [
        "오버워치",
        "오버워치2",
        "오버워치 2",
        "Overwatch 2",
        "OW2"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/2357570/Overwatch_2/",
        "publisher": "Blizzard Entertainment",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_listing"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3",
              "label": "Intel Core i3",
              "kind": "family"
            },
            {
              "id": "amd-phenom-x3-8650",
              "label": "AMD Phenom X3 8650",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-600-series",
              "label": "NVIDIA GeForce GTX 600 series",
              "kind": "family"
            },
            {
              "id": "amd-radeon-hd-7000-series",
              "label": "AMD Radeon HD 7000 series",
              "kind": "family"
            }
          ],
          "ram_gb": 6,
          "vram_gb": null,
          "storage_gb": 50,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7",
              "label": "Intel Core i7",
              "kind": "family"
            },
            {
              "id": "amd-ryzen-5",
              "label": "AMD Ryzen 5",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model"
            },
            {
              "id": "nvidia-geforce-gtx-1650",
              "label": "NVIDIA GeForce GTX 1650",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r9-380",
              "label": "AMD Radeon R9 380",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6400",
              "label": "AMD Radeon RX 6400",
              "kind": "model"
            },
            {
              "id": "intel-arc-a770",
              "label": "Intel Arc A770",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 50,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "CPU families and GPU series have no exact model specified.",
        "No resolution, preset, FPS, VRAM or disk type stated.",
        "Windows 10 64-bit; DirectX 11."
      ]
    },
    {
      "game_id": "valorant",
      "name": "VALORANT",
      "aliases": [
        "발로란트",
        "발로",
        "Valorant"
      ],
      "source": {
        "url": "https://support.riotgames.com/en-us/valorant/support-tools/minimum-recommended-pc-specs",
        "publisher": "Riot Games",
        "accessed_at": "2026-11-11",
        "updated_at": "2026-05-21",
        "kind": "official_support"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-540",
              "label": "Intel Core i3-540",
              "kind": "model"
            },
            {
              "id": "amd-athlon-200ge",
              "label": "AMD Athlon 200GE",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "intel-hd-4000",
              "label": "Intel HD 4000",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r5-220",
              "label": "AMD Radeon R5 220",
              "kind": "model"
            }
          ],
          "ram_gb": 4,
          "vram_gb": 1,
          "storage_gb": null,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": 30,
          "evidence_kind": "official_target",
          "vram_applies_to": "discrete_gpu_only"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-4150",
              "label": "Intel Core i3-4150",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-1200",
              "label": "AMD Ryzen 3 1200",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gt-730",
              "label": "NVIDIA GeForce GT 730",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r7-240",
              "label": "AMD Radeon R7 240",
              "kind": "model"
            }
          ],
          "ram_gb": 4,
          "vram_gb": 1,
          "storage_gb": null,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": 60,
          "evidence_kind": "official_target",
          "vram_applies_to": "discrete_gpu_only"
        },
        {
          "id": "high_end",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-9400f",
              "label": "Intel Core i5-9400F",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-2600x",
              "label": "AMD Ryzen 5 2600X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1050-ti",
              "label": "NVIDIA GeForce GTX 1050 Ti",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r7-370",
              "label": "AMD Radeon R7 370",
              "kind": "model"
            },
            {
              "id": "intel-arc-a310",
              "label": "Intel Arc A310",
              "kind": "model"
            }
          ],
          "ram_gb": 4,
          "vram_gb": 1,
          "storage_gb": null,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": 144,
          "evidence_kind": "official_target",
          "vram_applies_to": "discrete_gpu_only"
        }
      ],
      "notes": [
        "FPS values are official tier labels, not independently measured benchmarks.",
        "Resolution, preset and storage capacity are not specified.",
        "SSE4.2 or AVX; DirectX11; Windows11 requires TPM2.0 and UEFI Secure Boot."
      ]
    },
    {
      "game_id": "league_of_legends",
      "name": "League of Legends",
      "aliases": [
        "리그 오브 레전드",
        "리그오브레전드",
        "롤",
        "LoL"
      ],
      "source": {
        "url": "https://support.riotgames.com/en-us/league-of-legends/performance/minimum-and-recommended-system-requirements-league-of-legends",
        "publisher": "Riot Games",
        "accessed_at": "2026-11-11",
        "updated_at": "2026-09-22",
        "kind": "official_support"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-530",
              "label": "Intel Core i3-530",
              "kind": "model"
            },
            {
              "id": "amd-fx-4100",
              "label": "AMD FX-4100",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-400-series",
              "label": "NVIDIA GeForce 400 series",
              "kind": "family"
            },
            {
              "id": "amd-radeon-hd-6570",
              "label": "AMD Radeon HD 6570",
              "kind": "model"
            },
            {
              "id": "intel-hd-4600",
              "label": "Intel HD 4600",
              "kind": "model"
            }
          ],
          "ram_gb": 2,
          "vram_gb": 1,
          "storage_gb": 16,
          "storage_type": "HDD",
          "resolution": "1024x768",
          "preset": "Low",
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-8250",
              "label": "Intel Core i5-8250",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-1200",
              "label": "AMD Ryzen 3 1200",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-560",
              "label": "NVIDIA GeForce GTX 560",
              "kind": "model"
            },
            {
              "id": "amd-radeon-hd-6950",
              "label": "AMD Radeon HD 6950",
              "kind": "model"
            },
            {
              "id": "intel-uhd-630",
              "label": "Intel UHD 630",
              "kind": "model"
            }
          ],
          "ram_gb": 4,
          "vram_gb": 2,
          "storage_gb": 16,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": "High",
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "FPS is not specified.",
        "Source spells recommended NVIDIA card GeForce 560; normalized GTX560 is a naming interpretation, not a separate performance measurement.",
        "SSE4.2 and DirectX11 feature level11_0 required; excludes macOS table."
      ]
    },
    {
      "game_id": "pubg",
      "name": "PUBG: BATTLEGROUNDS",
      "aliases": [
        "배틀그라운드",
        "배그",
        "PUBG",
        "Battlegrounds"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/578080/PUBG_BATTLEGROUNDS/",
        "publisher": "KRAFTON",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_listing"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-4430",
              "label": "Intel Core i5-4430",
              "kind": "model"
            },
            {
              "id": "amd-fx-6300",
              "label": "AMD FX-6300",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-960",
              "label": "NVIDIA GeForce GTX 960",
              "kind": "model",
              "vram_gb": 2
            },
            {
              "id": "amd-radeon-r7-370",
              "label": "AMD Radeon R7 370",
              "kind": "model",
              "vram_gb": 2
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 40,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-6600k",
              "label": "Intel Core i5-6600K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-1600",
              "label": "AMD Ryzen 5 1600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model",
              "vram_gb": 3
            },
            {
              "id": "amd-radeon-rx-580",
              "label": "AMD Radeon RX 580",
              "kind": "model",
              "vram_gb": 4
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 50,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Per-GPU VRAM is specified; do not replace GTX1060 3GB with6GB silently.",
        "Resolution, preset, FPS and disk type not specified.",
        "Windows10 64-bit; DirectX11."
      ]
    },
    {
      "game_id": "counter_strike_2",
      "name": "Counter-Strike 2",
      "aliases": [
        "카운터 스트라이크2",
        "카운터스트라이크2",
        "카스2",
        "CS2",
        "Counter Strike 2"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/730/CounterStrike_2/",
        "publisher": "Valve",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_listing"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-750",
              "label": "Intel Core i5-750",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [],
          "ram_gb": 8,
          "vram_gb": 1,
          "storage_gb": 85,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "cpu_hardware_threads_min": 4,
          "gpu_features": [
            "DirectX 11",
            "Shader Model 5.0"
          ]
        }
      ],
      "notes": [
        "Only minimum published; no recommended tier or named Windows GPU model.",
        "Do not invent recommended GPU or infer FPS from generic minimum.",
        "Resolution, preset and FPS not specified; Windows10."
      ]
    },
    {
      "game_id": "fortnite",
      "name": "Fortnite",
      "aliases": [
        "포트나이트",
        "포나"
      ],
      "source": {
        "url": "https://www.epicgames.com/help/c-44968506/c-0/a16548002?lang=en-US",
        "publisher": "Epic Games",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "official_support"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-3225",
              "label": "Intel Core i3-3225",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "intel-hd-4000",
              "label": "Intel HD 4000",
              "kind": "model"
            },
            {
              "id": "amd-radeon-vega-8",
              "label": "AMD Radeon Vega 8",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": null,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-7300u",
              "label": "Intel Core i5-7300U",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-3300u",
              "label": "AMD Ryzen 3 3300U",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-960",
              "label": "NVIDIA GeForce GTX 960",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r9-280",
              "label": "AMD Radeon R9 280",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": 2,
          "storage_gb": null,
          "storage_type": "NVMe SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "epic_quality",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-8700",
              "label": "Intel Core i7-8700",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-7-3700x",
              "label": "AMD Ryzen 7 3700X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-3070",
              "label": "NVIDIA GeForce RTX 3070",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6700-xt",
              "label": "AMD Radeon RX 6700 XT",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": 8,
          "storage_gb": null,
          "storage_type": "NVMe SSD",
          "resolution": null,
          "preset": "Epic",
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Epic Quality is a distinct preset profile; do not use it for unspecified competitive/Performance Mode requests.",
        "No FPS, resolution or free storage capacity published in this support table.",
        "Recommended CPUs include mobile U-series parts; no invented desktop conversion."
      ]
    },
    {
      "game_id": "apex_legends",
      "name": "Apex Legends",
      "aliases": [
        "에이펙스 레전드",
        "에이펙스",
        "에펙",
        "Apex"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/1172470/Apex_Legends/",
        "publisher": "Electronic Arts / Respawn",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_listing"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "amd-fx-4350",
              "label": "AMD FX-4350",
              "kind": "model"
            },
            {
              "id": "intel-core-i3-6300",
              "label": "Intel Core i3-6300",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "amd-radeon-hd-7790",
              "label": "AMD Radeon HD 7790",
              "kind": "model",
              "vram_gb": 2
            },
            {
              "id": "nvidia-geforce-gtx-950",
              "label": "NVIDIA GeForce GTX 950",
              "kind": "model"
            }
          ],
          "ram_gb": 6,
          "vram_gb": null,
          "storage_gb": 75,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "amd-ryzen-5",
              "label": "AMD Ryzen 5",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "amd-radeon-r9-290",
              "label": "AMD Radeon R9 290",
              "kind": "model"
            },
            {
              "id": "nvidia-geforce-gtx-970",
              "label": "NVIDIA GeForce GTX 970",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 75,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Recommended CPU is family-only, no exact SKU.",
        "Current listing DirectX12; older DX11/GT640 sources are not imported.",
        "Only HD7790 VRAM2GB explicitly stated; GTX950 VRAM unknown in source.",
        "FPS, resolution, preset and disk type unspecified; localized language adds about3.8GB."
      ]
    },
    {
      "game_id": "cyberpunk_2077",
      "name": "Cyberpunk 2077",
      "aliases": [
        "사이버펑크2077",
        "사이버펑크 2077",
        "사펑",
        "Cyberpunk"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/1091500/_2077/?curator_clanid=30637343&l=english",
        "publisher": "CD PROJEKT RED",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_listing"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-6700",
              "label": "Intel Core i7-6700",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-1600",
              "label": "AMD Ryzen 5 1600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model",
              "vram_gb": 6
            },
            {
              "id": "amd-radeon-rx-580",
              "label": "AMD Radeon RX 580",
              "kind": "model",
              "vram_gb": 8
            },
            {
              "id": "intel-arc-a380",
              "label": "Intel Arc A380",
              "kind": "model"
            }
          ],
          "ram_gb": 12,
          "vram_gb": null,
          "storage_gb": 70,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-12700",
              "label": "Intel Core i7-12700",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-7-7800x3d",
              "label": "AMD Ryzen 7 7800X3D",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-2060-super",
              "label": "NVIDIA GeForce RTX 2060 SUPER",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-5700-xt",
              "label": "AMD Radeon RX 5700 XT",
              "kind": "model"
            },
            {
              "id": "intel-arc-a770",
              "label": "Intel Arc A770",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 70,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Current Windows listing only; excludes macOS and old pre2.0 requirements.",
        "FPS, resolution, preset, ray tracing and upscaling are unspecified in this listing.",
        "GTX1060 minimum6GB and RX580 minimum8GB are explicit; other GPU VRAM unspecified.",
        "DirectX12; SSD required."
      ]
    }
  ]
}
```
