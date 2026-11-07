from datetime import datetime, timedelta, timezone

import pytest

from pcquote.catalog import Catalog, Part

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)

ALL_SOCKETS = ["AM5", "AM4", "LGA1700", "LGA1851"]


def part(id, category, name, price, bench=None, bench_name=None, brand=None, rank=None, rank_age_days=1, **specs):
    observed = NOW - timedelta(days=rank_age_days) if rank else None
    return Part(id=id, category=category, name=name, price=price, brand=brand, specs=specs,
                benchmark=bench, benchmark_name=bench_name or name,
                popularity_rank=rank, popularity_observed_at=observed)


def sample_parts() -> list[Part]:
    return [
        part("c-7500f", "cpu", "AMD 라이젠5-5세대 7500F (라파엘) (멀티팩 정품)", 170_000, 66, "AMD Ryzen 5 7500F",
             brand="AMD", socket="AM5", watts=88, tdp=65, igpu=False),
        part("c-9600x", "cpu", "AMD 라이젠5-6세대 9600X (그래니트 릿지)", 280_000, 83, "AMD Ryzen 5 9600X",
             brand="AMD", socket="AM5", watts=88, tdp=65, igpu=True),
        part("c-9800x3d", "cpu", "AMD 라이젠7-6세대 9800X3D (그래니트 릿지)", 700_000, 150, "AMD Ryzen 7 9800X3D",
             brand="AMD", socket="AM5", watts=162, tdp=120, igpu=True),
        part("c-14400f", "cpu", "인텔 코어i5-14세대 14400F (랩터레이크 리프레시)", 171_000, 77, "Intel Core i5-14400F",
             brand="Intel", socket="LGA1700", watts=148, tdp=65, igpu=False),
        part("c-13400", "cpu", "인텔 코어i5-13세대 13400 (랩터레이크)", 230_000, 73, "Intel Core i5-13400",
             brand="Intel", socket="LGA1700", watts=154, tdp=65, igpu=True),
        part("c-245kf", "cpu", "인텔 코어 울트라5 시리즈2 245KF (애로우레이크)", 250_000, 130, "Intel Core Ultra 5 245KF",
             brand="Intel", socket="LGA1851", watts=159, tdp=125, igpu=False),
        part("g-4060", "gpu", "RTX 4060 8GB", 400_000, 74, "NVIDIA GeForce RTX 4060",
             watts=115, length=240, vram=8, connector="8pin", minPsu=550),
        part("g-5060ti", "gpu", "RTX 5060 Ti 16GB", 550_000, 100, "NVIDIA GeForce RTX 5060 Ti",
             watts=180, length=280, vram=16, connector="8pin", minPsu=600),
        part("g-5070", "gpu", "RTX 5070 12GB", 800_000, 143, "NVIDIA GeForce RTX 5070",
             watts=250, length=300, vram=12, connector="12v2x6", minPsu=650),
        part("g-5070ti", "gpu", "RTX 5070 Ti 16GB", 1_100_000, 176, "NVIDIA GeForce RTX 5070 Ti",
             watts=300, length=330, vram=16, connector="12v2x6", minPsu=750),
        part("g-5090", "gpu", "RTX 5090 32GB", 4_000_000, 347, "NVIDIA GeForce RTX 5090",
             watts=575, length=360, vram=32, connector="12v2x6", minPsu=1000),
        part("b-b650", "board", "MSI PRO B650M-A WIFI", 150_000, socket="AM5", ddr=5, form="mATX", slots=4,
             maxRam=192, m2=2, wifi=True),
        part("b-b850", "board", "ASRock B850M Pro RS", 190_000, socket="AM5", ddr=5, form="mATX", slots=4,
             maxRam=256, m2=3, wifi=False),
        part("b-b760", "board", "GIGABYTE B760M DS3H GEN5", 135_000, socket="LGA1700", ddr=5, form="mATX", slots=4,
             maxRam=256, m2=2, wifi=False),
        part("b-b860", "board", "GIGABYTE B860M DS3H", 165_000, socket="LGA1851", ddr=5, form="mATX", slots=4,
             maxRam=256, m2=2, wifi=False),
        part("b-h610", "board", "ASUS PRIME H610M-K D4", 80_000, socket="LGA1700", ddr=4, form="mATX", slots=2,
             maxRam=64, m2=1, wifi=False),
        part("r-16", "ram", "DDR5-5600 16GB (8Gx2)", 60_000, ddr=5, capacity=16, sticks=2),
        part("r-32", "ram", "DDR5-5600 32GB (16Gx2)", 110_000, ddr=5, capacity=32, sticks=2),
        part("r-64", "ram", "DDR5-5600 64GB (32Gx2)", 220_000, ddr=5, capacity=64, sticks=2),
        part("s-500", "ssd", "NVMe 500GB", 55_000, capacity=500, m2=1, interface="nvme"),
        part("s-1t", "ssd", "NVMe 1TB", 90_000, capacity=1000, m2=1, interface="nvme"),
        part("s-2t", "ssd", "NVMe 2TB", 160_000, capacity=2000, m2=1, interface="nvme"),
        part("p-650", "psu", "650W 80PLUS Bronze", 75_000, capacity=650, efficiency="브론즈", connectors=["8pin"]),
        part("p-850", "psu", "850W 80PLUS Gold ATX3.1", 130_000, capacity=850, efficiency="골드", connectors=["8pin", "12v2x6"]),
        part("p-1200", "psu", "1200W 80PLUS Platinum", 300_000, capacity=1200, efficiency="플래티넘", connectors=["8pin", "12v2x6"]),
        part("k-black", "case", "미들타워 블랙", 70_000, forms=["ATX", "mATX"], gpuLength=380, coolerHeight=165,
             color="black"),
        part("k-white", "case", "미들타워 화이트", 85_000, forms=["ATX", "mATX"], gpuLength=380, coolerHeight=165,
             color="white"),
        part("f-air", "cooler", "싱글타워 공랭", 35_000, sockets=ALL_SOCKETS, height=155, coolingWatts=200),
        part("f-aio", "cooler", "360 수랭 쿨러 AIO", 150_000, sockets=ALL_SOCKETS, height=55, coolingWatts=300),
    ]


@pytest.fixture
def catalog() -> Catalog:
    return Catalog(sample_parts(), now=NOW)
