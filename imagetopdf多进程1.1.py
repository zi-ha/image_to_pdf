import os
from PIL import Image
import sys
import concurrent.futures
import re # For natural sorting
from tqdm import tqdm # For progress bars


def natural_sort_key(s):
    """Key function for natural sorting (e.g., 'image1.jpg', 'image2.jpg', 'image10.jpg')."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', s)]

def process_image(image_path):
    """Opens, converts, and returns a single image object, ready for PDF."""
    try:
        img = Image.open(image_path)
        # Ensure image is in RGB format for PDF compatibility
        if img.mode == 'CMYK':
            # Pillow's default RGB conversion from CMYK is generally good
            print(f"警告：图片 {os.path.basename(image_path)} 是 CMYK 模式，尝试转换为 RGB。效果可能不完美。")
            img = img.convert('RGB')
        elif img.mode == 'RGBA' or img.mode == 'P': # P is palette mode
            # Convert RGBA or Palette images to RGB
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            # Attempt conversion for other modes, might need specific handling
            print(f"警告：图片 {os.path.basename(image_path)} 的模式为 {img.mode}，尝试转换为 RGB。")
            img = img.convert('RGB')
        return img
    except Exception as e:
        print(f"错误：无法打开或处理图片 {image_path}: {e}")
        # Raise the exception to be caught by the caller
        raise

def merge_images_to_pdf(folder_path, output_pdf_path):
    """Merges images in a folder into a single PDF file with natural sorting and progress."""
    image_files = []
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff")
    try:
        # Use natural sorting for filenames
        filenames = sorted(os.listdir(folder_path), key=natural_sort_key)
        for filename in filenames:
            if filename.lower().endswith(valid_extensions):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    image_files.append(file_path)
    except FileNotFoundError:
        print(f"错误：找不到文件夹 {folder_path}")
        return False # Indicate failure
    except Exception as e:
        print(f"读取文件夹 {folder_path} 时出错: {e}")
        return False # Indicate failure

    if not image_files:
        print(f"在文件夹 {folder_path} 中未找到有效图片文件。")
        return True # Indicate success (nothing to do)

    images_to_append = []
    first_image = None
    processed_image_objects = [] # Keep track to close them later

    try:
        # print(f"处理文件夹 '{os.path.basename(folder_path)}' 中的图片...") # Commented out this line
        # Process images without the inner progress bar
        for image_path in image_files:
            try:
                img = process_image(image_path)
                processed_image_objects.append(img) # Add to list for closing
                if first_image is None:
                    first_image = img
                else:
                    images_to_append.append(img)
            except Exception:
                # Error already printed in process_image, stop processing this folder
                return False # Indicate failure

        if first_image:
            first_image.save(output_pdf_path, save_all=True, append_images=images_to_append)
            # print(f"成功创建 PDF: {output_pdf_path}") # Keep output clean, success indicated by main loop
            return True # Indicate success
        else:
            print(f"文件夹 {folder_path} 中没有可处理的图片。")
            return True # Indicate success (no images processed)

    except Exception as e:
        print(f"创建 PDF {output_pdf_path} 时出错: {e}")
        return False # Indicate failure
    finally:
        # Ensure all opened image objects are closed
        # print(f"Closing {len(processed_image_objects)} images for {os.path.basename(folder_path)}") # Debugging
        for img in processed_image_objects:
            try:
                img.close()
            except Exception as close_err:
                print(f"关闭图片时出错: {close_err}")

def get_script_directory():
    """Determines the directory where the script is located."""
    if getattr(sys, 'frozen', False):
        # Bundled executable
        return os.path.dirname(sys.executable)
    else:
        # Normal .py file
        return os.path.dirname(os.path.abspath(__file__))

def find_folders_to_process(base_dir):
    """Finds subdirectories in the base_dir to process, skipping specific ones and existing PDFs."""
    folders = []
    skipped_folders = ['build', 'dist', '__pycache__', '.git', '.vscode'] # Add more if needed
    print(f"在 '{base_dir}' 中查找子文件夹...")
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            if item.lower() in skipped_folders:
                print(f"  - 跳过特殊文件夹: {item}")
                continue

            pdf_filename = f"{item}.pdf"
            output_pdf_path = os.path.join(base_dir, pdf_filename)

            if os.path.exists(output_pdf_path):
                print(f"  - PDF 文件 '{pdf_filename}' 已存在，跳过文件夹 '{item}'。")
                continue

            print(f"  + 找到待处理文件夹: {item}")
            folders.append((item_path, output_pdf_path, item))
    return folders

def process_folders_concurrently(folders_to_process, max_workers):
    """Processes a list of folders concurrently using ThreadPoolExecutor and tqdm."""
    processed_count = 0
    total_folders = len(folders_to_process)
    print(f"\n准备使用最多 {max_workers} 个进程并行处理 {total_folders} 个文件夹...")

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        future_to_folder = {executor.submit(merge_images_to_pdf, item_path, output_pdf_path): folder_name
                            for item_path, output_pdf_path, folder_name in folders_to_process}

        # Process completed tasks with a progress bar for folders
        for future in tqdm(concurrent.futures.as_completed(future_to_folder), total=total_folders, desc="整体进度", unit="个文件夹"):
            folder_name = future_to_folder[future]
            try:
                success = future.result() # Get result (True/False) or capture exceptions
                if success:
                    # print(f"文件夹 '{folder_name}' 处理成功。") # Keep output clean
                    processed_count += 1
                else:
                    print(f"文件夹 '{folder_name}' 处理失败或被中止。")
            except Exception as exc:
                print(f"文件夹 '{folder_name}' 处理时产生严重错误: {exc}")
                # Optionally, log the full traceback here
                # import traceback
                # traceback.print_exc()

    return processed_count

def main():
    script_dir = get_script_directory()
    print(f"脚本运行目录: {script_dir}")

    folders_to_process = find_folders_to_process(script_dir)

    if not folders_to_process:
        print("\n未找到需要处理的新子文件夹。")
    else:
        # Adjust max_workers based on your system's capabilities and potential memory usage
        # Consider reducing workers if memory consumption is high
        max_workers = max(1, (os.cpu_count() or 4) // 2) # Start more conservatively
        processed_count = process_folders_concurrently(folders_to_process, max_workers)
        print(f"\n处理完成！成功处理了 {processed_count} 个子文件夹。")


if __name__ == "__main__":
    # Check for dependencies
    missing_libs = []
    try:
        from PIL import Image
    except ImportError:
        missing_libs.append("Pillow")
    try:
        from tqdm import tqdm
    except ImportError:
        missing_libs.append("tqdm")

    if missing_libs:
        print("错误：缺少必要的库:", ", ".join(missing_libs))
        print("请使用 pip 安装:")
        for lib in missing_libs:
             print(f"  pip install {lib}")
        # Try installing automatically (optional, requires user confirmation or runs directly)
        # install_confirm = input("是否尝试自动安装缺失的库? (y/n): ")
        # if install_confirm.lower() == 'y':
        #     import subprocess
        #     for lib in missing_libs:
        #         print(f"正在安装 {lib}...")
        #         subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
        #     print("库安装完成，请重新运行脚本。")
        # else:
        #     print("请手动安装库后重试。")
        input("\n按 Enter 键退出...") # Keep window open
        sys.exit(1)

    main()
    input("\n所有操作已完成。按 Enter 键退出...") # Keep window open
