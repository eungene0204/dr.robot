# Additional game requirements: expansion A

Accessed **2026-11-11**. Ten Windows-PC games; **19 official requirement profiles** (Dota2 only publishes minimum). These are publisher requirements, not measured game benchmarks. Unspecified fields remain null. No page displayed a requirement-table revision date, so updated_at is null. Korean/English aliases are service normalization rather than performance facts.

## Verified primary sources and caveats

- [Dota2 / Valve Steam listing](https://store.steampowered.com/app/570/): minimum4GB/60GB, generic dual-core2.8GHz CPU and legacy GPU families. No recommended/FPS/preset tier. The listing's Windows7 text coexists with Steam's Windows10-or-later client notice.
- [Rust / Facepunch Steam listing](https://store.steampowered.com/app/252490/): minimum12GB, recommended16GB, both45GB; current Windows11 scope. SSD recommended at minimum and required at recommended. No VRAM or FPS stated.
- [GTA V Enhanced / Rockstar Steam listing](https://store.steampowered.com/app/3240220/): Enhanced edition only,105GB SSD. Recommended explicitly names RTX3060 **8GB** or RX6600XT8GB and DirectStorage-compatible SSD. Legacy cannot inherit these facts.
- [Red Dead Redemption2 / Rockstar Steam appdetails](https://store.steampowered.com/api/appdetails?appids=1174180&l=english&cc=us): PC payload opened directly because the human product page was age-gated.8/12GB RAM and150GB storage; per-alternative GPU VRAM retained. No SSD/FPS condition published.
- [ELDEN RING / publisher Steam listing](https://store.steampowered.com/app/1245620/): base game, not Nightreign.12/16GB RAM,60GB, minimumGTX1060 **3GB** orRX580 **4GB**, recommendedGTX1070/RXVega56 **8GB**. No FPS/preset claim.
- [Baldur's Gate3 / Larian Steam appdetails](https://store.steampowered.com/api/appdetails?appids=1086940&l=english&cc=us): opened directly; Windows minimum now includes SnapdragonXElite/AdrenoX1 andArcA380, recommendedArcA580. Profile VRAM floors4/8GB, SSD150GB, RAM8/16GB. No desktop equivalence or FPS inferred.
- [Black Myth Wukong / Game Science Steam listing](https://store.steampowered.com/app/2358720/):16GB RAM and130GB. Both profiles tested with DLSS/FSR/XeSS **enabled**; this is not native-render evidence. MinimumHDD supported/SSD recommended, recommendedSSD required.
- [Monster Hunter Wilds / Capcom Steam listing](https://store.steampowered.com/app/2246340/): current75GB SSD/16GB RAM. Publisher minimum1080p30 is **720p upscaled, Lowest**. Recommended1080p60 is **Medium, Frame Generation enabled**. Preserve those qualifications; neither is an independent benchmark or no-FG60 proof.
- [Helldivers2 / PlayStation Steam appdetails](https://store.steampowered.com/api/appdetails?appids=553850&l=english&cc=us): opened directly; minimum8GB/135GB and recommended16GB/**40GB** are internally inconsistent storage figures. Preserve them with explicit warning; recommended SSD is advisory. No FPS or per-model VRAM given.
- [Palworld / Pocketpair Steam listing](https://store.steampowered.com/app/1623730/): current minimum16GB/GTX1660, recommended32GB/RTX3060Ti orRX6700XT, both40GB SSD. Performance varies with activePals; these are client requirements, not dedicated-server sizing.

## Machine-readable seed

GPU alternative VRAM is only populated when explicitly stated. Profile-wide VRAM floors remain separate. Hardware labels expand conventional vendor abbreviations (e.g. source “Nvidia2060Super” to “NVIDIA GeForce RTX2060Super”) without asserting new performance equivalence. Edition is explicit in GTA Enhanced aliases; unqualified GTA aliases are deliberately omitted for edition disambiguation by the consuming application.

```json
{
  "schema_version": 1,
  "accessed_at": "2026-11-11",
  "games": [
    {
      "game_id": "dota_2",
      "name": "Dota 2",
      "aliases": [
        "도타 2",
        "도타2",
        "도타",
        "DOTA2"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/570/",
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
              "id": "intel-or-amd-dual-core-2-8-ghz",
              "label": "Intel or AMD dual-core 2.8 GHz",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-8600",
              "label": "NVIDIA GeForce 8600",
              "kind": "family"
            },
            {
              "id": "nvidia-geforce-9600-gt",
              "label": "NVIDIA GeForce 9600 GT",
              "kind": "model"
            },
            {
              "id": "ati-amd-radeon-hd-2600",
              "label": "ATI AMD Radeon HD 2600",
              "kind": "family"
            },
            {
              "id": "ati-amd-radeon-hd-3600",
              "label": "ATI AMD Radeon HD 3600",
              "kind": "family"
            }
          ],
          "ram_gb": 4,
          "vram_gb": null,
          "storage_gb": 60,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows minimum only; no recommended tier, exact CPU SKU, VRAM, FPS, resolution or preset published.",
        "Listing still names Windows 7, while the same page says Steam client requires Windows 10 or later since 2024-01-01.",
        "GeForce 8600 and Radeon HD2600/3600 are source family labels; do not invent exact variant equivalences."
      ]
    },
    {
      "game_id": "rust",
      "name": "Rust",
      "aliases": [
        "러스트"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/252490/",
        "publisher": "Facepunch Studios",
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
              "id": "amd-ryzen-5-1400",
              "label": "AMD Ryzen 5 1400",
              "kind": "model"
            },
            {
              "id": "intel-core-i5-6600",
              "label": "Intel Core i5-6600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "amd-radeon-rx-470",
              "label": "AMD Radeon RX 470",
              "kind": "model"
            },
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model"
            },
            {
              "id": "intel-arc-a580",
              "label": "Intel Arc A580",
              "kind": "model"
            }
          ],
          "ram_gb": 12,
          "vram_gb": null,
          "storage_gb": 45,
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
              "id": "amd-ryzen-7-3700x",
              "label": "AMD Ryzen 7 3700X",
              "kind": "model"
            },
            {
              "id": "intel-core-i7-6700k",
              "label": "Intel Core i7-6700K",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "amd-radeon-rx-6600-xt",
              "label": "AMD Radeon RX 6600 XT",
              "kind": "model"
            },
            {
              "id": "nvidia-geforce-rtx-3060",
              "label": "NVIDIA GeForce RTX 3060",
              "kind": "model"
            },
            {
              "id": "intel-arc-b580",
              "label": "Intel Arc B580",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 45,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows 11 64-bit; minimum SSD highly recommended but not explicitly required, recommended SSD required.",
        "Source does not specify GPU VRAM, FPS, resolution or preset."
      ]
    },
    {
      "game_id": "gta_v_enhanced",
      "name": "Grand Theft Auto V Enhanced",
      "aliases": [
        "GTA V Enhanced",
        "GTA5 Enhanced",
        "GTA 5 Enhanced",
        "GTA5 인핸스드",
        "GTA 5 인핸스드",
        "GTA V 인핸스드",
        "그랜드 테프트 오토 V 인핸스드"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/3240220/",
        "publisher": "Rockstar Games",
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
              "id": "intel-core-i7-4770",
              "label": "Intel Core i7-4770",
              "kind": "model"
            },
            {
              "id": "amd-fx-9590",
              "label": "AMD FX-9590",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1630",
              "label": "NVIDIA GeForce GTX 1630",
              "kind": "model",
              "vram_gb": 4
            },
            {
              "id": "amd-radeon-rx-6400",
              "label": "AMD Radeon RX 6400",
              "kind": "model",
              "vram_gb": 4
            }
          ],
          "ram_gb": 8,
          "vram_gb": 4,
          "storage_gb": 105,
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
              "id": "intel-core-i5-9600k",
              "label": "Intel Core i5-9600K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3600",
              "label": "AMD Ryzen 5 3600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-3060",
              "label": "NVIDIA GeForce RTX 3060",
              "kind": "model",
              "vram_gb": 8
            },
            {
              "id": "amd-radeon-rx-6600-xt",
              "label": "AMD Radeon RX 6600 XT",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 16,
          "vram_gb": 8,
          "storage_gb": 105,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "storage_features": [
            "DirectStorage-compatible"
          ]
        }
      ],
      "notes": [
        "Enhanced edition only; not the Legacy edition. Unqualified GTA5/GTA V aliases intentionally excluded here because edition is ambiguous.",
        "Minimum Windows10, recommended Windows11. Recommended SSD must support DirectStorage.",
        "Source explicitly specifies RTX3060 8GB, not the 12GB variant. No FPS, resolution or preset in requirements."
      ]
    },
    {
      "game_id": "red_dead_redemption_2",
      "name": "Red Dead Redemption 2",
      "aliases": [
        "레드 데드 리뎀션 2",
        "레드데드리뎀션2",
        "레데리2",
        "레데리 2",
        "RDR2",
        "RDR 2"
      ],
      "source": {
        "url": "https://store.steampowered.com/api/appdetails?appids=1174180&l=english&cc=us",
        "publisher": "Rockstar Games",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_appdetails"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-2500k",
              "label": "Intel Core i5-2500K",
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
              "id": "nvidia-geforce-gtx-770",
              "label": "NVIDIA GeForce GTX 770",
              "kind": "model",
              "vram_gb": 2
            },
            {
              "id": "amd-radeon-r9-280",
              "label": "AMD Radeon R9 280",
              "kind": "model",
              "vram_gb": 3
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 150,
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
              "id": "intel-core-i7-4770k",
              "label": "Intel Core i7-4770K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-1500x",
              "label": "AMD Ryzen 5 1500X",
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
              "id": "amd-radeon-rx-480",
              "label": "AMD Radeon RX 480",
              "kind": "model",
              "vram_gb": 4
            }
          ],
          "ram_gb": 12,
          "vram_gb": null,
          "storage_gb": 150,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows10 64-bit. Source does not require SSD or specify FPS, resolution or preset.",
        "Steam product page is age-gated in research browser; source is the same publisher-managed Steam appdetails PC requirement payload."
      ]
    },
    {
      "game_id": "elden_ring",
      "name": "ELDEN RING",
      "aliases": [
        "엘든 링",
        "엘든링"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/1245620/",
        "publisher": "FromSoftware, Inc. / Bandai Namco Entertainment",
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
              "id": "intel-core-i5-8400",
              "label": "Intel Core i5-8400",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-3300x",
              "label": "AMD Ryzen 3 3300X",
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
          "ram_gb": 12,
          "vram_gb": null,
          "storage_gb": 60,
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
              "id": "intel-core-i7-8700k",
              "label": "Intel Core i7-8700K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3600x",
              "label": "AMD Ryzen 5 3600X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1070",
              "label": "NVIDIA GeForce GTX 1070",
              "kind": "model",
              "vram_gb": 8
            },
            {
              "id": "amd-radeon-rx-vega-56",
              "label": "AMD Radeon RX Vega 56",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 16,
          "vram_gb": 8,
          "storage_gb": 60,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Original ELDEN RING base-game Windows requirements, not ELDEN RING NIGHTREIGN.",
        "DirectX12; no SSD, FPS, resolution or preset specified."
      ]
    },
    {
      "game_id": "baldurs_gate_3",
      "name": "Baldur's Gate 3",
      "aliases": [
        "발더스 게이트 3",
        "발더스게이트3",
        "발더스3",
        "발더스 3",
        "BG3",
        "Baldurs Gate 3"
      ],
      "source": {
        "url": "https://store.steampowered.com/api/appdetails?appids=1086940&l=english&cc=us",
        "publisher": "Larian Studios",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_appdetails"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-4690",
              "label": "Intel Core i5-4690",
              "kind": "model"
            },
            {
              "id": "amd-fx-8350",
              "label": "AMD FX-8350",
              "kind": "model"
            },
            {
              "id": "qualcomm-snapdragon-x-elite",
              "label": "Qualcomm Snapdragon X Elite",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-970",
              "label": "NVIDIA GeForce GTX 970",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-480",
              "label": "AMD Radeon RX 480",
              "kind": "model"
            },
            {
              "id": "intel-arc-a380",
              "label": "Intel Arc A380",
              "kind": "model"
            },
            {
              "id": "qualcomm-adreno-x1",
              "label": "Qualcomm Adreno X1",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": 4,
          "storage_gb": 150,
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
              "id": "intel-core-i7-8700k",
              "label": "Intel Core i7-8700K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3600",
              "label": "AMD Ryzen 5 3600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-2060-super",
              "label": "NVIDIA GeForce RTX 2060 Super",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-5700-xt",
              "label": "AMD Radeon RX 5700 XT",
              "kind": "model"
            },
            {
              "id": "intel-arc-a580",
              "label": "Intel Arc A580",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": 8,
          "storage_gb": 150,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Current Windows PC payload explicitly lists Snapdragon X Elite/Adreno X1 among minimum alternatives; preserve these mobile/ARM labels without desktop equivalence.",
        "GPU groups specify 4GB+ and 8GB+ VRAM. Those are profile floors; do not invent per-model VRAM variants.",
        "DirectX11; no FPS, resolution or preset stated. Publisher-managed Steam appdetails used because product page is age-gated."
      ]
    },
    {
      "game_id": "black_myth_wukong",
      "name": "Black Myth: Wukong",
      "aliases": [
        "검은 신화 오공",
        "검은신화오공",
        "검은 신화: 오공",
        "오공",
        "Black Myth Wukong"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/2358720/",
        "publisher": "Game Science",
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
              "id": "intel-core-i5-8400",
              "label": "Intel Core i5-8400",
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
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 130,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "upscaling": true
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-9700",
              "label": "Intel Core i7-9700",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-5500",
              "label": "AMD Ryzen 5 5500",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-2060",
              "label": "NVIDIA GeForce RTX 2060",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-5700-xt",
              "label": "AMD Radeon RX 5700 XT",
              "kind": "model"
            },
            {
              "id": "intel-arc-a750",
              "label": "Intel Arc A750",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 130,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "upscaling": true
        }
      ],
      "notes": [
        "Both published profiles were tested with DLSS/FSR/XeSS enabled; they do not establish native-rendering performance.",
        "Minimum permits HDD and recommends SSD; recommended requires SSD.",
        "No FPS, resolution, preset or frame-generation state specified; recommended GPU VRAM is not stated."
      ]
    },
    {
      "game_id": "monster_hunter_wilds",
      "name": "Monster Hunter Wilds",
      "aliases": [
        "몬스터 헌터 와일즈",
        "몬스터헌터와일즈",
        "몬헌 와일즈",
        "몬헌와일즈",
        "몬헌 와일드",
        "MHWs"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/2246340/",
        "publisher": "CAPCOM Co., Ltd.",
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
              "id": "intel-core-i5-10400",
              "label": "Intel Core i5-10400",
              "kind": "model"
            },
            {
              "id": "intel-core-i3-12100",
              "label": "Intel Core i3-12100",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3600",
              "label": "AMD Ryzen 5 3600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1660",
              "label": "NVIDIA GeForce GTX 1660",
              "kind": "model",
              "vram_gb": 6
            },
            {
              "id": "amd-radeon-rx-5500-xt",
              "label": "AMD Radeon RX 5500 XT",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 75,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": "Lowest",
          "target_fps": 30,
          "evidence_kind": "official_requirements",
          "upscaling": true,
          "native_resolution": "1280x720",
          "frame_generation": null,
          "storage_features": [
            "DirectStorage-supported"
          ]
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-10400",
              "label": "Intel Core i5-10400",
              "kind": "model"
            },
            {
              "id": "intel-core-i3-12100",
              "label": "Intel Core i3-12100",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3600",
              "label": "AMD Ryzen 5 3600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-2060-super",
              "label": "NVIDIA GeForce RTX 2060 Super",
              "kind": "model",
              "vram_gb": 8
            },
            {
              "id": "amd-radeon-rx-6600",
              "label": "AMD Radeon RX 6600",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 16,
          "vram_gb": 8,
          "storage_gb": 75,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": "Medium",
          "target_fps": 60,
          "evidence_kind": "official_requirements",
          "frame_generation": true,
          "upscaling": null,
          "storage_features": [
            "DirectStorage-supported"
          ]
        }
      ],
      "notes": [
        "Publisher expected performance labels, not independent measurements: minimum 1080p30 is upscaled from native720p at Lowest; recommended1080p60 is Medium WITH Frame Generation enabled.",
        "Do not interpret recommended60fps as native rendered60fps or use it to guarantee stable/no-FG60.",
        "Current Steam requirements specify75GB storage and16GB RAM, not older launch120/140GB figures."
      ]
    },
    {
      "game_id": "helldivers_2",
      "name": "HELLDIVERS 2",
      "aliases": [
        "헬다이버즈 2",
        "헬다이버즈2",
        "헬다이버2",
        "헬다이버 2",
        "Helldivers II"
      ],
      "source": {
        "url": "https://store.steampowered.com/api/appdetails?appids=553850&l=english&cc=us",
        "publisher": "PlayStation Publishing LLC",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "publisher_steam_appdetails"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-4790k",
              "label": "Intel Core i7-4790K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-1500x",
              "label": "AMD Ryzen 5 1500X",
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
              "id": "amd-radeon-rx-470",
              "label": "AMD Radeon RX 470",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 135,
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
              "id": "intel-core-i7-9700k",
              "label": "Intel Core i7-9700K",
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
              "id": "nvidia-geforce-rtx-2060",
              "label": "NVIDIA GeForce RTX 2060",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6600-xt",
              "label": "AMD Radeon RX 6600 XT",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 40,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Current official Steam appdetails payload inconsistently specifies135GB minimum and40GB recommended; values are preserved rather than silently harmonized. Storage coverage needs recheck before promising installation space.",
        "Recommended SSD is advisory (SSD Recommended), not a requirement in this payload.",
        "No VRAM, resolution, preset or FPS stated. Steam product page age-gated; publisher-managed appdetails opened directly."
      ]
    },
    {
      "game_id": "palworld",
      "name": "Palworld",
      "aliases": [
        "팔월드",
        "팰월드",
        "팰 월드",
        "팔 월드"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/1623730/",
        "publisher": "Pocketpair",
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
              "id": "intel-core-i5-9400f",
              "label": "Intel Core i5-9400F",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1660",
              "label": "NVIDIA GeForce GTX 1660",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 40,
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
              "id": "intel-core-i5-12400",
              "label": "Intel Core i5-12400",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-5600x",
              "label": "AMD Ryzen 5 5600X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-3060-ti",
              "label": "NVIDIA GeForce RTX 3060 Ti",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6700-xt",
              "label": "AMD Radeon RX 6700 XT",
              "kind": "model"
            }
          ],
          "ram_gb": 32,
          "vram_gb": null,
          "storage_gb": 40,
          "storage_type": "SSD",
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Current PC listing uses minimumGTX1660 and recommended32GB RAM; do not reuse outdated Early Access GTX1050 figures.",
        "SSD required for both tiers. Publisher warns performance depends on active Pals. No VRAM, resolution, preset or FPS stated.",
        "Client requirements only; no dedicated-server sizing inference."
      ]
    }
  ]
}
```
