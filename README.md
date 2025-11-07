# PDF OCR 批量处理工具

批量对PDF文件进行OCR识别，保留原始格式、布局和图片，生成可搜索的PDF。

## 安装步骤

### 1. 安装 Tesseract OCR

**Windows:**
- 下载安装包: https://github.com/UB-Mannheim/tesseract/wiki
- 安装时选择中文语言包 (Chinese Simplified)
- 添加到系统PATH: `C:\Program Files\Tesseract-OCR`

**验证安装:**
```bash
tesseract --version
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python pdf_ocr_batch.py
```

1. 选择包含PDF文件的输入文件夹
2. 选择输出文件夹
3. 等待处理完成

## 功能特点

- ✓ 保留原始PDF格式和布局
- ✓ 支持中英文识别
- ✓ 批量处理多个文件
- ✓ 多线程并行处理
- ✓ 图形界面选择文件夹
- ✓ 实时显示处理进度

