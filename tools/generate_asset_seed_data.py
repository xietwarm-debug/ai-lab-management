#!/usr/bin/env python3
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from random import Random


DEFAULT_LABS = [
    ("计算机实验室A101", "信息楼A座101", "张老师"),
    ("计算机实验室A102", "信息楼A座102", "李老师"),
    ("计算机实验室B201", "信息楼B座201", "王老师"),
    ("计算机实验室B202", "信息楼B座202", "赵老师"),
]

DEFAULT_OPEN_HOURS = "08:00-21:30"
DEFAULT_CAPACITY = 60


@dataclass(frozen=True)
class AssetTemplate:
    prefix: str
    name: str
    model: str
    brand: str
    unit_price: int
    quantity: int
    allow_borrow: bool = False
    spec: dict | None = None


LAB_ASSET_TEMPLATES = [
    AssetTemplate("HOST", "学生机主机", "OptiPlex 7090", "Dell", 5200, 30, spec={"category": "computer", "role": "student_host"}),
    AssetTemplate("MON", "学生机显示器", "ThinkVision T24i", "Lenovo", 980, 30, spec={"category": "computer", "role": "student_monitor"}),
    AssetTemplate("KEY", "学生机键盘", "KB216", "Dell", 89, 30, spec={"category": "computer_accessory"}),
    AssetTemplate("MOU", "学生机鼠标", "MS116", "Dell", 59, 30, spec={"category": "computer_accessory"}),
    AssetTemplate("HEAD", "语音耳机", "H390", "Logitech", 159, 30, spec={"category": "audio"}),
    AssetTemplate("DESK", "学生实验桌", "双人位实验桌", "鸿合", 860, 30, spec={"category": "furniture"}),
    AssetTemplate("CHAIR", "学生椅", "人体工学学生椅", "震旦", 280, 60, spec={"category": "furniture"}),
    AssetTemplate("TDESK", "教师办公桌", "T-Desk-1600", "中伟", 1280, 1, spec={"category": "furniture"}),
    AssetTemplate("TCHR", "教师椅", "Ergo-Teacher", "震旦", 680, 1, spec={"category": "furniture"}),
    AssetTemplate("POD", "讲台", "Podium-01", "海捷", 1680, 1, spec={"category": "furniture"}),
    AssetTemplate("TPC", "教师机主机", "ProDesk 600", "HP", 6200, 1, spec={"category": "computer", "role": "teacher_host"}),
    AssetTemplate("TMON", "教师机显示器", "P24v", "HP", 1180, 1, spec={"category": "computer", "role": "teacher_monitor"}),
    AssetTemplate("SW", "接入交换机", "S1730S-L24T4S-A", "Huawei", 2600, 2, spec={"category": "network"}),
    AssetTemplate("RTR", "路由器", "AR1220", "Huawei", 3200, 1, spec={"category": "network"}),
    AssetTemplate("AP", "无线AP", "AP6050DN", "Huawei", 1350, 2, spec={"category": "network"}),
    AssetTemplate("PROJ", "投影仪", "CB-X51", "Epson", 4200, 1, spec={"category": "teaching_device"}),
    AssetTemplate("SCR", "投影幕布", "120寸电动幕布", "红叶", 980, 1, spec={"category": "teaching_device"}),
    AssetTemplate("SPK", "音箱", "教室壁挂音箱", "漫步者", 560, 2, spec={"category": "audio"}),
    AssetTemplate("PRN", "打印机", "M437nda", "HP", 3800, 1, spec={"category": "office"}),
    AssetTemplate("UPS", "UPS电源", "C1K", "山特", 2200, 1, spec={"category": "power"}),
    AssetTemplate("AC", "空调", "KFR-72LW", "格力", 5600, 2, spec={"category": "facility"}),
    AssetTemplate("LGT", "LED照明灯", "600x600面板灯", "欧普", 180, 12, spec={"category": "facility"}),
    AssetTemplate("CAM", "监控摄像头", "DS-2CD3T47", "海康威视", 480, 2, spec={"category": "security"}),
    AssetTemplate("ACS", "门禁控制器", "DS-K2602", "海康威视", 1650, 1, spec={"category": "security"}),
    AssetTemplate("WB", "白板", "磁性白板", "得力", 420, 1, spec={"category": "teaching_device"}),
    AssetTemplate("CAB", "文件柜", "铁皮资料柜", "中伟", 820, 2, spec={"category": "office"}),
    AssetTemplate("FIRE", "灭火器", "4KG干粉灭火器", "桂安", 95, 2, spec={"category": "safety"}),
    AssetTemplate("PDU", "插排", "8位防雷插排", "公牛", 96, 20, spec={"category": "power"}),
    AssetTemplate("CABLE", "网线盘", "六类网线100米", "安普", 480, 4, spec={"category": "network"}),
    AssetTemplate("CUR", "窗帘", "遮光窗帘", "金蝉", 260, 6, spec={"category": "facility"}),
    AssetTemplate("TOOL", "运维工具箱", "IT-Tool-01", "世达", 650, 1, True, spec={"category": "maintenance"}),
    AssetTemplate("LAP", "备用笔记本", "ThinkBook 14", "Lenovo", 5200, 2, True, spec={"category": "portable_computer"}),
    AssetTemplate("HDMI", "HDMI转接器", "Type-C转HDMI", "绿联", 89, 6, True, spec={"category": "adapter"}),
    AssetTemplate("SCAN", "手持扫码枪", "DS2208", "Zebra", 980, 1, True, spec={"category": "portable_device"}),
]


def normalize_lab_code(lab_name: str) -> str:
    letters = []
    for ch in lab_name.upper():
        if ch.isascii() and ch.isalnum():
            letters.append(ch)
    text = "".join(letters)
    return text[-4:] if len(text) >= 4 else (text or "LABX")


def parse_lab_items(raw_labs: str | None):
    if not raw_labs:
        return DEFAULT_LABS
    rows = []
    for index, part in enumerate(raw_labs.split(","), start=1):
        name = part.strip()
        if not name:
            continue
        rows.append((name, f"测试楼{index:02d}室", f"管理员{index:02d}"))
    return rows or DEFAULT_LABS


def build_purchase_date(rng: Random) -> str:
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def build_status(rng: Random, template: AssetTemplate) -> str:
    if template.prefix in {"FIRE", "LGT", "CUR"}:
        return "in_service"
    roll = rng.random()
    if roll < 0.93:
        return "in_service"
    if roll < 0.985:
        return "repairing"
    return "scrapped"


def build_price(rng: Random, base_price: int) -> int:
    jitter = rng.randint(-8, 8) / 100.0
    return max(10, int(round(base_price * (1 + jitter))))


def write_lab_seed_file(path: Path, labs):
    lines = []
    for name, location, manager in labs:
        lines.append(",".join([name, location, str(DEFAULT_CAPACITY), manager, DEFAULT_OPEN_HOURS, ""]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_equipment_seed_file(path: Path, labs, rng: Random):
    headers = [
        "asset_code",
        "name",
        "lab_name",
        "model",
        "brand",
        "keeper",
        "price",
        "status",
        "purchase_date",
        "spec_json",
        "allow_borrow",
    ]
    count = 0
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for lab_name, _location, keeper in labs:
            lab_code = normalize_lab_code(lab_name)
            for template in LAB_ASSET_TEMPLATES:
                for index in range(1, template.quantity + 1):
                    asset_code = f"{lab_code}-{template.prefix}-{index:03d}"
                    spec = dict(template.spec or {})
                    spec["labCode"] = lab_code
                    spec["seedBatch"] = "asset-demo-20260321"
                    row = {
                        "asset_code": asset_code,
                        "name": template.name,
                        "lab_name": lab_name,
                        "model": template.model,
                        "brand": template.brand,
                        "keeper": keeper,
                        "price": build_price(rng, template.unit_price),
                        "status": build_status(rng, template),
                        "purchase_date": build_purchase_date(rng),
                        "spec_json": json.dumps(spec, ensure_ascii=False, separators=(",", ":")),
                        "allow_borrow": "1" if template.allow_borrow else "0",
                    }
                    writer.writerow(row)
                    count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Generate lab and equipment seed files for bulk import.")
    parser.add_argument("--out-dir", default="generated/asset-seed", help="Directory to write generated files into.")
    parser.add_argument(
        "--labs",
        default="",
        help="Comma-separated lab names. Example: 计算机实验室A101,计算机实验室A102",
    )
    parser.add_argument("--seed", type=int, default=20260321, help="Random seed for stable output.")
    args = parser.parse_args()

    labs = parse_lab_items(args.labs)
    rng = Random(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lab_file = out_dir / "lab_seed_import.txt"
    equipment_file = out_dir / "equipment_seed_import.csv"

    write_lab_seed_file(lab_file, labs)
    equipment_count = write_equipment_seed_file(equipment_file, labs, rng)

    summary = {
        "labCount": len(labs),
        "equipmentCount": equipment_count,
        "labFile": str(lab_file),
        "equipmentFile": str(equipment_file),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
