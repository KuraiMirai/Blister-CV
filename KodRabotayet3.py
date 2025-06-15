import cv2
import numpy as np
import os
import csv
import json
from datetime import datetime
import argparse
import matplotlib.pyplot as plt

class BlisterProcessor:
    def __init__(self):
        self.processed_files = set()
        self.setup_directories()
        self.load_processed_files()
        
    def setup_directories(self):
        """Инициализация папок для логов и графиков"""
        self.base_dir = "C:/Users/Mirai/Desktop/KURSACH"
        self.photos_dir = os.path.join(self.base_dir, "Photos")
        self.log_dir = os.path.join(self.base_dir, "DefectLogs")
        self.graph_dir = os.path.join(self.log_dir, "Graphs")
        self.reference_path = os.path.join(self.base_dir, "Ethalon/Ethalon.png")
        
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.graph_dir, exist_ok=True)
        
        self.log_file = os.path.join(self.log_dir, "defect_log.csv")
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "image_path", "blister_id", "defect_types", "areas", "circularities", "is_defective"])
    
    def load_processed_files(self):
        """Загружает список уже обработанных файлов"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    if len(row) > 1:
                        self.processed_files.add(os.path.basename(row[1]))
    
    def process_image(self, image_path):
        """Обрабатывает одно изображение и возвращает JSON результат"""
        try:
            filename = os.path.basename(image_path)
            defects = self.process_blister_image(image_path)
            blister_id = self.get_blister_id(filename)
            
            self.log_defect(image_path, blister_id, defects)
            self.processed_files.add(filename)
            
            return {
                "blister_id": blister_id,
                "has_defects": len(defects) > 0,
                "defect_count": len(defects),
                "defects": defects,
                "status": "success"
            }
        except Exception as e:
            error_msg = f"Ошибка обработки {os.path.basename(image_path)}: {str(e)}"
            print(error_msg)
            return {
                "blister_id": "error",
                "has_defects": False,
                "defect_count": 0,
                "status": error_msg
            }
    
    def process_blister_image(self, image_path):
        """Основная функция обработки изображения"""
        defects = []
        filename = os.path.basename(image_path)
        
        original = cv2.imread(image_path)
        reference = cv2.imread(self.reference_path)
        
        if original is None or reference is None:
            raise ValueError("Ошибка загрузки изображений")

        if original.shape != reference.shape:
            original = cv2.resize(original, (reference.shape[1], reference.shape[0]))

        gray_original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        gray_reference = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        
        diff = cv2.absdiff(gray_original, gray_reference)
        _, threshold_diff = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        kernel = np.ones((3, 3), np.uint8)
        cleaned_diff = cv2.morphologyEx(threshold_diff, cv2.MORPH_OPEN, kernel, iterations=2)
        
        contours, _ = cv2.findContours(cleaned_diff, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        min_area = 100
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            perimeter = cv2.arcLength(cnt, True)
            circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
            defect_type = self.classify_defect(area, circularity)

            x, y, w, h = cv2.boundingRect(cnt)
            defects.append({
                "id": i + 1,
                "type": defect_type,
                "area": area,
                "circularity": circularity,
                "bounding_box": (x, y, w, h)
            })

            cv2.drawContours(original, [cnt], -1, (0, 0, 255), 2)
            cv2.putText(original, f"{i+1}: {defect_type}", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

        self.save_graph(filename, reference, original, cleaned_diff)
        return defects
    
    def classify_defect(self, area, circularity):
        """Классификация дефектов (оригинальная логика)"""
        if circularity > 0.3 and area < 400:
            return "Вмятина"
        return "Трещина" if area > 200 else "Царапина"
    
    def save_graph(self, filename, reference, original, cleaned_diff):
        """Сохранение графиков сравнения"""
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
        plt.title("Эталон")
        plt.axis('off')
        
        plt.subplot(1, 3, 2)
        plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        plt.title("Дефекты")
        plt.axis('off')
        
        plt.subplot(1, 3, 3)
        plt.imshow(cleaned_diff, cmap='gray')
        plt.title("Маска дефектов")
        plt.axis('off')
        
        graph_filename = os.path.join(self.graph_dir, f"{os.path.splitext(filename)[0]}_graph.png")
        plt.savefig(graph_filename, bbox_inches='tight', dpi=150)
        plt.close()
    
    def log_defect(self, image_path, blister_id, defects):
        """Логирование результатов в CSV"""
        is_defective = len(defects) > 0
        defect_types = "; ".join([d['type'] for d in defects]) if defects else "Нет дефектов"
        areas = "; ".join([str(d['area']) for d in defects]) if defects else "0"
        circularities = "; ".join([str(d['circularity']) for d in defects]) if defects else "0"
        
        with open(self.log_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                image_path,
                blister_id,
                defect_types,
                areas,
                circularities,
                is_defective
            ])
    
    def get_blister_id(self, filename):
        """Извлечение ID из имени файла"""
        parts = filename.split('_')
        return parts[1] if len(parts) > 1 else "unknown"

def main():
    """Режим работы из командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Path to single image to process")
    args = parser.parse_args()

    processor = BlisterProcessor()
    
    if args.image:
        # Режим для Unity - обработка одного изображения
        result = processor.process_image(args.image)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Автономный режим - мониторинг папки
        print("Blister Processor запущен. Ожидание новых фотографий...")
        while True:
            new_photos = processor.get_new_photos()
            for photo in new_photos:
                photo_path = os.path.join(processor.photos_dir, photo)
                result = processor.process_image(photo_path)
                print(f"Обработано: {photo} | Дефектов: {result['defect_count']}")
            time.sleep(1)

if __name__ == "__main__":
    import time
    main()