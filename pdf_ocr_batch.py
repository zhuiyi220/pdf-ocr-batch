import ocrmypdf
import os
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import multiprocessing
import fitz
from PIL import Image, ImageEnhance, ImageFilter
import io
import tempfile

os.environ['PATH'] = r'C:\Program Files\Tesseract-OCR' + os.pathsep + r'C:\Program Files\gs\bin' + os.pathsep + os.environ['PATH']

def select_folder(title):
    root = Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder

def check_image_quality(img):
    gray = img.convert('L')
    pixels = list(gray.getdata())
    avg_brightness = sum(pixels) / len(pixels)
    variance = sum((p - avg_brightness) ** 2 for p in pixels) / len(pixels)
    contrast = variance ** 0.5
    
    is_low_quality = avg_brightness < 100 or avg_brightness > 200 or contrast < 30
    return is_low_quality, avg_brightness, contrast

def enhance_image(img):
    img = img.convert('RGB')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.3)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    return img

def preprocess_pdf(input_path, output_path, filename):
    doc = fitz.open(input_path)
    enhanced_doc = fitz.open()
    
    needs_enhancement = False
    total_pages = len(doc)
    
    print(f"  → 检测图像质量: {filename} ({total_pages}页)")
    
    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        is_low_quality, brightness, contrast = check_image_quality(img)
        
        if is_low_quality:
            if not needs_enhancement:
                print(f"  → 发现低质量页面，开始增强处理...")
            needs_enhancement = True
            img = enhance_image(img)
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        new_page = enhanced_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=img_bytes.getvalue())
        
        if (page_num + 1) % 5 == 0 or page_num == total_pages - 1:
            print(f"  → 预处理进度: {page_num + 1}/{total_pages}")
    
    enhanced_doc.save(output_path)
    enhanced_doc.close()
    doc.close()
    
    return needs_enhancement

def process_pdf(input_path, output_path, skip_existing=True):
    filename = os.path.basename(input_path)
    
    if skip_existing and os.path.exists(output_path):
        return True, f"{filename} (已跳过)", False
    
    try:
        print(f"\n开始处理: {filename}")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            temp_path = tmp.name
        
        enhanced = preprocess_pdf(input_path, temp_path, filename)
        
        print(f"  → 开始OCR识别...")
        
        ocrmypdf.ocr(
            temp_path,
            output_path,
            language='chi_sim+chi_tra+eng',
            redo_ocr=True,
            optimize=1,
            tesseract_timeout=300,
            tesseract_oem=1,
            output_type='pdf',
            pdf_renderer='sandwich',
            jobs=2,
            progress_bar=False
        )
        
        os.unlink(temp_path)
        
        print(f"  ✓ 完成: {filename} {'[已增强]' if enhanced else ''}")
        
        status = f"{filename} {'[已增强]' if enhanced else ''}"
        return True, status, enhanced
    except Exception as e:
        print(f"  ✗ 失败: {filename}")
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        return False, f"{filename}: {str(e)}", False

def main():
    input_folder = select_folder("选择输入文件夹（包含PDF文件）")
    if not input_folder:
        print("未选择输入文件夹，程序退出")
        return
    
    output_folder = select_folder("选择输出文件夹")
    if not output_folder:
        print("未选择输出文件夹，程序退出")
        return
    
    pdf_files = list(Path(input_folder).glob("*.pdf"))
    
    if not pdf_files:
        messagebox.showinfo("提示", "输入文件夹中没有PDF文件")
        return
    
    log_file = os.path.join(output_folder, f"ocr_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    print(f"找到 {len(pdf_files)} 个PDF文件，开始处理...\n")
    print(f"日志文件: {log_file}")
    print(f"自动图像增强: 开启\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    enhanced_count = 0
    
    max_workers = max(1, multiprocessing.cpu_count() // 2)
    
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"OCR处理日志 - {datetime.now()}\n")
        log.write(f"输入目录: {input_folder}\n")
        log.write(f"输出目录: {output_folder}\n")
        log.write(f"文件总数: {len(pdf_files)}\n")
        log.write(f"启用自动图像增强\n\n")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for pdf_file in pdf_files:
                output_path = os.path.join(output_folder, pdf_file.name)
                future = executor.submit(process_pdf, str(pdf_file), output_path)
                futures[future] = pdf_file.name
            
            for future in as_completed(futures):
                success, message, enhanced = future.result()
                if success:
                    if "已跳过" in message:
                        skipped_count += 1
                        status = "⊙"
                    else:
                        success_count += 1
                        status = "✓"
                        if enhanced:
                            enhanced_count += 1
                    print(f"{status} [{success_count + failed_count + skipped_count}/{len(pdf_files)}] {message}")
                    log.write(f"{status} {message}\n")
                else:
                    failed_count += 1
                    print(f"✗ [{success_count + failed_count + skipped_count}/{len(pdf_files)}] {message}")
                    log.write(f"✗ {message}\n")
        
        summary = f"\n处理完成！成功: {success_count}, 跳过: {skipped_count}, 失败: {failed_count}, 增强: {enhanced_count}"
        print(summary)
        log.write(summary)
    
    messagebox.showinfo("完成", f"处理完成！\n成功: {success_count}\n跳过: {skipped_count}\n失败: {failed_count}\n图像增强: {enhanced_count}\n\n日志: {log_file}")

if __name__ == "__main__":
    main()
