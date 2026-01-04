import os
import json
import time
import sys
import inspect
import warnings
from PIL import Image

warnings.filterwarnings("ignore")

try:
    from surya.foundation import FoundationPredictor
    from surya.detection import DetectionPredictor
    from surya.recognition import RecognitionPredictor
    from surya.layout import LayoutPredictor
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# --- НАСТРОЙКИ ---
IMAGE_PATH = r"F:\Скани\СканиПНГ\АкваАльянс Установчі\Adobe Scan 20 Dec 2025 (46)\page_1.png"
LANGS = ["uk", "ru", "cs", "en"]

print("📥 Шаг 1: Загрузка моделей...")
fp = FoundationPredictor()
dp = DetectionPredictor()
lp = LayoutPredictor(fp)
rp = RecognitionPredictor(fp)

# --- ШАГ 2: ИНТРОСПЕКЦИЯ (УЗНАЕМ ИМЕНА АРГУМЕНТОВ) ---
print("🔍 Шаг 2: Анализ API RecognitionPredictor...")
sig = inspect.signature(rp.__call__)
params = sig.parameters.keys()
print(f"Доступные параметры: {list(params)}")

# Автоматически определяем, какое имя использовать для языков
lang_key = None
if "langs" in params: lang_key = "langs"
elif "languages" in params: lang_key = "languages"

# --- ШАГ 3: БЫСТРАЯ ПРОВЕРКА (DRY RUN) ---
print("🧪 Шаг 3: Быстрая проверка (Dry Run)...")
try:
    test_img = Image.new('RGB', (20, 20), color='white')
    # Проверяем Layout
    _ = lp(images=[test_img])
    
    # Готовим аргументы для OCR динамически
    ocr_args = {"images": [test_img], "det_predictor": dp}
    if lang_key:
        ocr_args[lang_key] = [LANGS]
    
    _ = rp(**ocr_args)
    print("✅ API проверено, аргументы подобраны автоматически!")
except Exception as e:
    print(f"❌ Ошибка на этапе проверки: {e}")
    sys.exit(1)

# --- ШАГ 4: РЕАЛЬНАЯ РАБОТА ---
def process_file(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    print(f"\n🚀 Обработка: {os.path.basename(path)} ({w}x{h})")
    
    # 1. Layout
    t1 = time.time()
    l_preds = lp(images=[img])
    print(f"⏱️ Layout: {time.time()-t1:.1f}с")
    
    # 2. OCR
    t2 = time.time()
    real_ocr_args = {"images": [img], "det_predictor": dp}
    if lang_key:
        real_ocr_args[lang_key] = [LANGS]
    
    o_preds = rp(**real_ocr_args)
    print(f"⏱️ OCR: {time.time()-t2:.1f}с")

    # 3. Сборка
    detections = []
    for i, box_item in enumerate(l_preds[0].bboxes):
        b = box_item.bbox
        text_parts = []
        for line in o_preds[0].text_lines:
            cx, cy = (line.bbox[0] + line.bbox[2])/2, (line.bbox[1] + line.bbox[3])/2
            if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
                text_parts.append(line.text)
        
        detections.append({
            "text": " ".join(text_parts).strip(),
            "type": str(box_item.label).lower(),
            "box_2d": [int(b[1]/h*1000), int(b[0]/w*1000), int(b[3]/h*1000), int(b[2]/w*1000)],
            "reading_order": i + 1
        })
    return detections

try:
    final = process_file(IMAGE_PATH)
    with open("surya_final_result.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 ПОБЕДА! Результат в surya_final_result.json")
except Exception as e:
    print(f"💀 Критическая ошибка: {e}")