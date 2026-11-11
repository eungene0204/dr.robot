# 추가 인기 게임 공식 사양 조사 B

확인일 **2026-11-11**. 아래 10게임의 공식 지원 문서·게임사 다운로드 페이지·퍼블리셔 관리 Steam 상품 페이지를 열어 Windows PC 사양을 확인했다. 공식 요구 사양과 원본 실측을 구별하며, 공개되지 않은 값은 `null`로 남긴다. Steam 표는 appdetails의 `pc_requirements` HTML도 대조했다. 공식 사양의 업데이트 날짜가 없으면 임의로 추정하지 않는다.

## 출처와 적용 범위

- [Bungie의 Destiny 2 Steam 표](https://store.steampowered.com/app/1085660/Destiny_2/): 최소·권장 CPU/GPU와 GPU별 VRAM을 분리했다. 105GB 표에는 2020년 기준·증가 가능성 주석이 있어 현재 전체 설치량을 검증한 값으로 쓰면 안 된다.
- [Digital Extremes의 Warframe Steam 표](https://store.steampowered.com/app/230410/Warframe/): 최소만 공개하며 GPU는 DX11+ 기능 조건이다. 권장 GPU/FPS를 만들지 않았다. Windows7 문구와 Steam Windows10+ 조건을 함께 보존했다.
- [Ubisoft의 현재 Rainbow Six Siege 표](https://store.steampowered.com/app/359550/Tom_Clancys_Rainbow_Six_Siege_X/): Siege X 이후 현재 CPU/GPU/DX12 표. 오래된 오리지널 출시 표와 혼합하지 않았다.
- [Behaviour의 Dead by Daylight 표](https://store.steampowered.com/app/381210/Dead_by_Daylight/): 최소 Low 설정, 권장 GPU4GB 문맥과 시스템 RAM8GB를 구별했다.
- [Grinding Gear Games의 Path of Exile 2 표](https://store.steampowered.com/app/2694490/Path_of_Exile_2/): 원문의 Ryzen5 3700X와 GTX960(3GB) 표기를 보존하고 이상 가능성을 명시했다. PoE1 표를 가져오지 않았다.
- [Blizzard의 Diablo IV 표](https://store.steampowered.com/app/2344520/Diablo_IV/): 최소는1080p 출력/720p 렌더 Low30, 권장은1080p Medium60. 두 tier 모두 SSD 필수. 이를 네이티브1080p 최소 성능 또는 원본 실측으로 해석하지 않았다.
- [HoYoverse 공식 Genshin Impact 도움말](https://support.hoyoverse.com/hc/en-us/articles/52089402685593-What-are-the-system-requirements-to-play-Genshin-Impact): 표시된 갱신일2025-11-11, 확인일2026-11-11. PC 기본 클라이언트110GB와 SSD 권고를 보존하고 별도 에디터 요구 사양을 섞지 않았다.
- [Mojang/Microsoft의 Java 시스템 사양 표](https://www.minecraft.net/en-us/store/minecraft-java-bedrock-edition-pc), [2026-07-21 사양 변경 공지](https://www.minecraft.net/en-us/article/minecraft-java-edition-system-requirements): Java Windows만 수록. 최소 외장8GB/내장12GB RAM과 권장16GB, FHD Fast30/Fancy60 목표를 구별했다. “마크”는 Java 기본 해석임을 명시해야 하며 Bedrock·모드·셰이더 성능을 보장하지 않는다.
- [Smilegate 한국 Lost Ark 다운로드 사양](https://lostark.game.onstove.com/Download): FHD 최소/권장, QHD/UHD 권장 4개. 60Hz는 별도 `refresh_rate_hz`로 저장했으며 FPS 값으로 바꾸지 않았다. UHD RAM32GB와 해상도별 CPU/GPU를 보존했다.
- [Nexon 한국 MapleStory 현재 다운로드 사양](https://maplestory.nexon.com/Common/PDS/Download): 현재 권장 표만 수록. 최소 tier를 과거 공지에서 되살리지 않았다. Worlds·Classic World·모바일과 구별한다.

## 기계 판독용 입력

`target_fps`는 퍼블리셔의 조건부 사양 목표일 뿐 측정값이 아니다. `resolution`은 픽셀 문자열이다. GPU 대안들은 AND 조건이 아니라 대안이며, CPU 제품군은 임의의 정확 모델로 바꾸지 않았다. `edition`/`region`/`notes`에 버전·지역 한계를 보존한다.

재확인 메모: 한국 Lost Ark 다운로드 페이지는 같은 날 선행 조회에서 클라이언트 사양표가 표시되어 수집했다. 후속 조회에서는 공식 점검 페이지로 리다이렉트되었다. 앞서 확인한 표의 값을 유지하며, 별도 HTML 스냅샷은 저장하지 않았다. 사이트 점검 자체를 사양 변경으로 해석하지 않는다.

```json
{
  "schema_version": 1,
  "accessed_at": "2026-11-11",
  "games": [
    {
      "game_id": "destiny_2",
      "name": "Destiny 2",
      "aliases": [
        "데스티니2",
        "데스티니 2",
        "데스티니 가디언즈",
        "Destiny 2"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/1085660/Destiny_2/",
        "publisher": "Bungie",
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
              "id": "intel-core-i3-3250",
              "label": "Intel Core i3-3250",
              "kind": "model"
            },
            {
              "id": "intel-pentium-g4560",
              "label": "Intel Pentium G4560",
              "kind": "model"
            },
            {
              "id": "amd-fx-4350",
              "label": "AMD FX-4350",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-660",
              "label": "NVIDIA GeForce GTX 660",
              "kind": "model",
              "vram_gb": 2
            },
            {
              "id": "nvidia-geforce-gtx-1050",
              "label": "NVIDIA GeForce GTX 1050",
              "kind": "model",
              "vram_gb": 2
            },
            {
              "id": "amd-radeon-hd-7850",
              "label": "AMD Radeon HD 7850",
              "kind": "model",
              "vram_gb": 2
            }
          ],
          "ram_gb": 6,
          "vram_gb": null,
          "storage_gb": 105,
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
              "id": "intel-core-i5-2400",
              "label": "Intel Core i5-2400",
              "kind": "model"
            },
            {
              "id": "intel-core-i5-7400",
              "label": "Intel Core i5-7400",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-1600x",
              "label": "AMD Ryzen 5 1600X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-970",
              "label": "NVIDIA GeForce GTX 970",
              "kind": "model",
              "vram_gb": 4
            },
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model",
              "vram_gb": 6
            },
            {
              "id": "amd-radeon-r9-390",
              "label": "AMD Radeon R9 390",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 105,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows 10 64-bit. No resolution, preset or FPS target is published in this table.",
        "105GB is the publisher Steam table value; its footer dates that storage baseline to November 10, 2020 and warns that storage requirements increase. It is not a verified current full installation size. The linked Bungie current storage page was inaccessible during this check."
      ]
    },
    {
      "game_id": "warframe",
      "name": "Warframe",
      "aliases": [
        "워프레임",
        "Warframe"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/230410/Warframe/",
        "publisher": "Digital Extremes",
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
              "id": "intel-core-i7-860",
              "label": "Intel Core i7-860",
              "kind": "model"
            },
            {
              "id": "intel-core-i5-750",
              "label": "Intel Core i5-750",
              "kind": "model"
            },
            {
              "id": "amd-fx-4100",
              "label": "AMD FX-4100",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [],
          "ram_gb": 4,
          "vram_gb": null,
          "storage_gb": 75,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "gpu_requirement": "DirectX 11+ capable graphics card",
          "cpu_instruction_requirement": "SSE4.2"
        }
      ],
      "notes": [
        "Publisher Steam listing publishes minimum only; no named GPU model, VRAM, recommended tier, resolution, preset or FPS target.",
        "The listing still prints Windows7 64-bit but separately states that the Steam client requires Windows10 or later. DX12 requires Windows10 20H2 or Windows11. Do not present Windows7 as a current deployable Steam recommendation.",
        "Official Warframe support minimum-spec page returned an access challenge; the publisher-maintained Steam table is the source used here."
      ]
    },
    {
      "game_id": "rainbow_six_siege_x",
      "name": "Tom Clancy's Rainbow Six Siege (Siege X PC requirements)",
      "aliases": [
        "레인보우 식스 시즈",
        "레인보우식스시즈",
        "레식",
        "시즈 X",
        "Siege X",
        "Rainbow Six Siege",
        "Rainbow Six Siege X"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/359550/Tom_Clancys_Rainbow_Six_Siege_X/",
        "publisher": "Ubisoft",
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
              "id": "amd-ryzen-3-3100",
              "label": "AMD Ryzen 3 3100",
              "kind": "model"
            },
            {
              "id": "intel-core-i3-8100",
              "label": "Intel Core i3-8100",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1650",
              "label": "NVIDIA GeForce GTX 1650",
              "kind": "model",
              "vram_gb": 4
            },
            {
              "id": "amd-radeon-rx-5500-xt",
              "label": "AMD Radeon RX 5500 XT",
              "kind": "model",
              "vram_gb": 4
            },
            {
              "id": "intel-arc-a380",
              "label": "Intel Arc A380",
              "kind": "model",
              "vram_gb": 6
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 65,
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
              "id": "amd-ryzen-5-3600",
              "label": "AMD Ryzen 5 3600",
              "kind": "model"
            },
            {
              "id": "intel-core-i5-10400",
              "label": "Intel Core i5-10400",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-2060",
              "label": "NVIDIA GeForce RTX 2060",
              "kind": "model",
              "vram_gb": 6
            },
            {
              "id": "amd-radeon-rx-6600",
              "label": "AMD Radeon RX 6600",
              "kind": "model",
              "vram_gb": 8
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 65,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Current app359550 publisher table after Siege X; the currently displayed store title is Rainbow Six Siege. This is not the older GTX460/GTX670 original-launch table.",
        "Minimum Windows10/11; recommended Windows11; DX12. No resolution, preset or FPS target is stated in the textual table. This does not establish Dual Front mode performance."
      ],
      "edition": "siege_x_current"
    },
    {
      "game_id": "dead_by_daylight",
      "name": "Dead by Daylight",
      "aliases": [
        "데드 바이 데이라이트",
        "데드바이데이라이트",
        "데바데",
        "Dead by Daylight"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/381210/Dead_by_Daylight/",
        "publisher": "Behaviour Interactive",
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
              "id": "intel-core-i3-4170",
              "label": "Intel Core i3-4170",
              "kind": "model"
            },
            {
              "id": "amd-fx-8120",
              "label": "AMD FX-8120",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-460",
              "label": "NVIDIA GeForce GTX 460",
              "kind": "model",
              "vram_gb": 1
            },
            {
              "id": "amd-radeon-hd-6850",
              "label": "AMD Radeon HD 6850",
              "kind": "model",
              "vram_gb": 1
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 50,
          "storage_type": null,
          "resolution": null,
          "preset": "low",
          "target_fps": null,
          "evidence_kind": "official_requirements"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-4170",
              "label": "Intel Core i3-4170",
              "kind": "model"
            },
            {
              "id": "amd-fx-8300",
              "label": "AMD FX-8300",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-760",
              "label": "NVIDIA GeForce 760 (source spelling)",
              "kind": "model",
              "vram_gb": 4
            },
            {
              "id": "amd-radeon-hd-8800",
              "label": "AMD Radeon HD 8800",
              "kind": "family",
              "vram_gb": 4
            }
          ],
          "ram_gb": 8,
          "vram_gb": 4,
          "storage_gb": 50,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows10 64-bit, DX11. Minimum notes recommend Low settings, but no resolution or FPS is stated.",
        "Recommended graphics line spells GeForce760 and HD8800 or higher with4GB of RAM. Preserve that source wording and GPU-memory context; do not reinterpret it as the separate system-memory requirement (8GB)."
      ]
    },
    {
      "game_id": "path_of_exile_2",
      "name": "Path of Exile 2",
      "aliases": [
        "패스 오브 엑자일2",
        "패스 오브 엑자일 2",
        "패스오브엑자일2",
        "POE2",
        "POE 2",
        "Path of Exile 2"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/2694490/Path_of_Exile_2/",
        "publisher": "Grinding Gear Games",
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
              "id": "intel-core-i7-7700",
              "label": "Intel Core i7-7700",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-2500x",
              "label": "AMD Ryzen 5 2500X",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-960",
              "label": "NVIDIA GeForce GTX 960",
              "kind": "model",
              "vram_gb": 3
            },
            {
              "id": "intel-arc-a380",
              "label": "Intel Arc A380",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-470",
              "label": "AMD Radeon RX 470",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": 3,
          "storage_gb": 100,
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
              "id": "intel-core-i5-10500",
              "label": "Intel Core i5-10500",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-3700x",
              "label": "AMD Ryzen 5 3700X (source spelling)",
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
              "id": "intel-arc-a770",
              "label": "Intel Arc A770",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-5600-xt",
              "label": "AMD Radeon RX 5600 XT",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 100,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "storage_recommendation": "SSD"
        }
      ],
      "notes": [
        "Path of Exile2 only, not PoE1. Windows10, DX12; source still labels the game Early Access.",
        "The original table says Ryzen5 3700X and GTX960(3GB). These unusual spellings/configurations are recorded verbatim as source facts, not silently corrected to Ryzen7 or a known2GB/4GB GTX960 variant.",
        "Minimum additional notes specify at least3GB VRAM for any GPU. Recommended notes recommend SSD. No resolution, preset or FPS target."
      ]
    },
    {
      "game_id": "diablo_iv",
      "name": "Diablo IV",
      "aliases": [
        "디아블로4",
        "디아블로 4",
        "디아4",
        "Diablo 4",
        "Diablo IV"
      ],
      "source": {
        "url": "https://store.steampowered.com/app/2344520/Diablo_IV/",
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
              "id": "intel-core-i5-2500k",
              "label": "Intel Core i5-2500K",
              "kind": "model"
            },
            {
              "id": "amd-fx-8350",
              "label": "AMD FX-8350",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-660",
              "label": "NVIDIA GeForce GTX 660",
              "kind": "model"
            },
            {
              "id": "intel-arc-a380",
              "label": "Intel Arc A380",
              "kind": "model"
            },
            {
              "id": "amd-radeon-r9-280",
              "label": "AMD Radeon R9 280",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 90,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": "low",
          "target_fps": 30,
          "evidence_kind": "official_requirements",
          "render_resolution": "1280x720"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-4670k",
              "label": "Intel Core i5-4670K",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-1300x",
              "label": "AMD Ryzen 3 1300X",
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
              "id": "intel-arc-a750",
              "label": "Intel Arc A750",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-470",
              "label": "AMD Radeon RX 470",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 90,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": "medium",
          "target_fps": 60,
          "evidence_kind": "official_requirements"
        }
      ],
      "notes": [
        "Windows10 64-bit1909+, DX12. Both tiers require SSD.",
        "Minimum source context is1080p display/native resolution with720p render resolution, Low30FPS; do not describe this as native-rendered1080p30.",
        "Recommended source context is1080p Medium60FPS. These are publisher requirements/targets, not benchmark measurements or a guarantee for another PC. The table spells AMD Ryzen1300X without a family number; model is identifiable as1300X."
      ]
    },
    {
      "game_id": "genshin_impact",
      "name": "Genshin Impact",
      "aliases": [
        "원신",
        "Genshin Impact"
      ],
      "source": {
        "url": "https://support.hoyoverse.com/hc/en-us/articles/52089402685593-What-are-the-system-requirements-to-play-Genshin-Impact",
        "publisher": "HoYoverse",
        "accessed_at": "2026-11-11",
        "updated_at": "2025-11-11",
        "kind": "official_support"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-6th-generation",
              "label": "Intel Core i5 6th generation",
              "kind": "family"
            },
            {
              "id": "amd-ryzen-series",
              "label": "AMD Ryzen series",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1050",
              "label": "NVIDIA GeForce GTX 1050",
              "kind": "model"
            },
            {
              "id": "intel-iris-xe",
              "label": "Intel Iris Xe",
              "kind": "family"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "storage_recommendation": "SSD"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i7-7th-generation",
              "label": "Intel Core i7 7th generation",
              "kind": "family"
            },
            {
              "id": "amd-ryzen-5000-series",
              "label": "AMD Ryzen 5000 series",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1060",
              "label": "NVIDIA GeForce GTX 1060",
              "kind": "model",
              "vram_gb": 6
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "storage_recommendation": "SSD"
        }
      ],
      "notes": [
        "Official help article updated November11,2025; current page checked November11,2026. Windows10 64-bit minimum, Windows10/11 recommended, DX11.",
        "Minimum allows either discrete GTX1050 or integrated IrisXe/equivalent. CPU families have no exact model. SSD is recommended, not stated mandatory. Storage can grow with future updates.",
        "No resolution, preset or FPS target is published; this is the normal PC client, not the separate Miliastra Sandbox editor requirements."
      ]
    },
    {
      "game_id": "minecraft_java",
      "name": "Minecraft: Java Edition",
      "aliases": [
        "마인크래프트",
        "마크",
        "마인크래프트 자바",
        "마크 자바",
        "Minecraft Java",
        "Minecraft Java Edition",
        "Minecraft: Java Edition"
      ],
      "source": {
        "url": "https://www.minecraft.net/en-us/store/minecraft-java-bedrock-edition-pc",
        "publisher": "Mojang Studios / Microsoft",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "official_product_requirements"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-10100",
              "label": "Intel Core i3-10100",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-3100",
              "label": "AMD Ryzen 3 3100",
              "kind": "model"
            },
            {
              "id": "qualcomm-snapdragon-x",
              "label": "Qualcomm Snapdragon X",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-950",
              "label": "NVIDIA GeForce GTX 950",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-460",
              "label": "AMD Radeon RX 460",
              "kind": "model"
            },
            {
              "id": "intel-arc-a310",
              "label": "Intel Arc A310",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": 2,
          "storage_gb": 2,
          "storage_type": null,
          "resolution": "1920x1080",
          "preset": "fast",
          "target_fps": 30,
          "evidence_kind": "official_requirements",
          "gpu_mode": "discrete",
          "graphics_api": "Vulkan 1.3",
          "cpu_cores_min": 4
        },
        {
          "id": "minimum_integrated",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-10100",
              "label": "Intel Core i3-10100",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-3100",
              "label": "AMD Ryzen 3 3100",
              "kind": "model"
            },
            {
              "id": "qualcomm-snapdragon-x",
              "label": "Qualcomm Snapdragon X",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "intel-core-i5-6400-integrated-graphics",
              "label": "Intel Core i5-6400 integrated graphics or newer",
              "kind": "family"
            },
            {
              "id": "qualcomm-snapdragon-x-integrated-graphics",
              "label": "Qualcomm Snapdragon X integrated graphics",
              "kind": "family"
            }
          ],
          "ram_gb": 12,
          "vram_gb": 2,
          "storage_gb": 2,
          "storage_type": null,
          "resolution": "1920x1080",
          "preset": "fast",
          "target_fps": 30,
          "evidence_kind": "official_requirements",
          "gpu_mode": "integrated",
          "graphics_api": "Vulkan 1.3",
          "cpu_cores_min": 4
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
              "id": "amd-ryzen-5-5600",
              "label": "AMD Ryzen 5 5600",
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
              "id": "amd-radeon-rx-5600-xt",
              "label": "AMD Radeon RX 5600 XT",
              "kind": "model"
            },
            {
              "id": "intel-arc-a580",
              "label": "Intel Arc A580",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": 6,
          "storage_gb": 4,
          "storage_type": null,
          "resolution": "1920x1080",
          "preset": "fancy",
          "target_fps": 60,
          "evidence_kind": "official_requirements",
          "graphics_api": "Vulkan 1.3"
        }
      ],
      "notes": [
        "Java Edition Windows scope only. Common aliases Minecraft/마인크래프트/마크 are ambiguous; this record explicitly defaults to Java, not Bedrock, and must be presented as such. No Bedrock GPU/RAM table is merged here.",
        "Official Java requirements changed July21,2026: FHD30 Fast minimum and FHD60 Fancy recommended. Source article: https://www.minecraft.net/en-us/article/minecraft-java-edition-system-requirements . Old2GB/4GB RAM Java figures are obsolete.",
        "Minimum8GB with discrete GPU versus12GB with integrated graphics; recommended16GB. Apple alternatives are excluded from Windows scope. Qualcomm Windows ARM remains explicit. Vulkan1.3 required; modpacks, shaders, ray tracing and dedicated server hosting are outside these baseline targets.",
        "Minimum Windows10 64-bit, recommended Windows11. Storage2GB minimum/4GB recommended comes from the same product-page FAQ, not world/mod size predictions."
      ],
      "edition": "java"
    },
    {
      "game_id": "lost_ark",
      "name": "Lost Ark (Korea)",
      "aliases": [
        "로스트아크",
        "로아",
        "Lost Ark"
      ],
      "source": {
        "url": "https://lostark.game.onstove.com/Download",
        "publisher": "Smilegate",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "official_download_requirements"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "minimum",
          "cpu_alternatives": [
            {
              "id": "intel-core-i3-10100",
              "label": "Intel Core i3-10100",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-3-3100",
              "label": "AMD Ryzen 3 3100",
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
              "id": "amd-radeon-rx-560",
              "label": "AMD Radeon RX 560",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": "HDD",
          "resolution": "1920x1080",
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "refresh_rate_hz": 60,
          "storage_recommendation": "SSD"
        },
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-9400",
              "label": "Intel Core i5-9400",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-2600",
              "label": "AMD Ryzen 5 2600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gtx-1660-super",
              "label": "NVIDIA GeForce GTX 1660 SUPER",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6600",
              "label": "AMD Radeon RX 6600",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": "SSD",
          "resolution": "1920x1080",
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "refresh_rate_hz": 60
        },
        {
          "id": "recommended_qhd",
          "cpu_alternatives": [
            {
              "id": "intel-core-i5-11400",
              "label": "Intel Core i5-11400",
              "kind": "model"
            },
            {
              "id": "amd-ryzen-5-5600",
              "label": "AMD Ryzen 5 5600",
              "kind": "model"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-rtx-3060",
              "label": "NVIDIA GeForce RTX 3060",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6600",
              "label": "AMD Radeon RX 6600",
              "kind": "model"
            }
          ],
          "ram_gb": 16,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": "SSD",
          "resolution": "2560x1440",
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "refresh_rate_hz": 60
        },
        {
          "id": "recommended_uhd",
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
              "id": "nvidia-geforce-rtx-3080",
              "label": "NVIDIA GeForce RTX 3080",
              "kind": "model"
            },
            {
              "id": "amd-radeon-rx-6800-xt",
              "label": "AMD Radeon RX 6800 XT",
              "kind": "model"
            }
          ],
          "ram_gb": 32,
          "vram_gb": null,
          "storage_gb": 110,
          "storage_type": "SSD",
          "resolution": "3840x2160",
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "refresh_rate_hz": 60
        }
      ],
      "notes": [
        "Korean Smilegate service, not the separate Amazon regional Steam table. Official columns are FHD minimum/recommended, QHD recommended and UHD recommended.",
        "All columns are stated for60Hz refresh rate; target_fps is unknown and remains null. No preset or per-GPU VRAM is stated. Do not turn60Hz into a measured or guaranteed60FPS.",
        "Windows10 64-bit (Windows11 recommended), DX11+. Minimum disk column says HDD110GB with SSD recommended; recommended columns require SSD110GB. Introductory installer note also advises110GB SSD free space."
      ],
      "region": "KR"
    },
    {
      "game_id": "maplestory",
      "name": "MapleStory (Korea)",
      "aliases": [
        "메이플스토리",
        "메이플",
        "MapleStory"
      ],
      "source": {
        "url": "https://maplestory.nexon.com/Common/PDS/Download",
        "publisher": "Nexon",
        "accessed_at": "2026-11-11",
        "updated_at": null,
        "kind": "official_download_requirements"
      },
      "platform": "windows_pc",
      "profiles": [
        {
          "id": "recommended",
          "cpu_alternatives": [
            {
              "id": "intel-pentium-dual-core",
              "label": "Intel Pentium Dual Core",
              "kind": "family"
            }
          ],
          "gpu_alternatives": [
            {
              "id": "nvidia-geforce-gt-430",
              "label": "NVIDIA GeForce GT 430",
              "kind": "model"
            },
            {
              "id": "amd-radeon-hd-5670",
              "label": "AMD Radeon HD 5670",
              "kind": "model"
            }
          ],
          "ram_gb": 8,
          "vram_gb": null,
          "storage_gb": 35,
          "storage_type": null,
          "resolution": null,
          "preset": null,
          "target_fps": null,
          "evidence_kind": "official_requirements",
          "gpu_shader_model": "3.0",
          "graphics_api": "DirectX 11"
        }
      ],
      "notes": [
        "Korean mainline MapleStory current official download page; not MapleStory Worlds, Classic World, MapleStory M or MapleStory Idle.",
        "Current page publishes recommended only: Windows10 64-bit+, Pentium Dual Core-class CPU,8GB RAM,35GB disk, GT430/HD5670-class graphics with Shader3.0+, DirectX11. No exact CPU model, VRAM, disk type, resolution, preset or FPS target. Do not invent a minimum tier from2012/2014 archived notices."
      ],
      "region": "KR"
    }
  ]
}
```
