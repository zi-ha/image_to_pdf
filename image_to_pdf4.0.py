import os
import zipfile
import tempfile
import shutil
from PIL import Image
import sys
import re
from tqdm import tqdm
import io
import concurrent.futures
import multiprocessing


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


def process_image_from_bytes(image_data, filename):
    """从字节数据处理图片，返回准备好的图片对象用于PDF。"""
    try:
        img = Image.open(io.BytesIO(image_data))
        # 确保图片是RGB格式以兼容PDF
        if img.mode == 'CMYK':
            print(f"警告：图片 {filename} 是 CMYK 模式，尝试转换为 RGB。效果可能不完美。")
            img = img.convert('RGB')
        elif img.mode == 'RGBA' or img.mode == 'P':  # P是调色板模式
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            print(f"警告：图片 {filename} 的模式为 {img.mode}，尝试转换为 RGB。")
            img = img.convert('RGB')
        return img
    except Exception as e:
        print(f"错误：无法打开或处理图片 {filename}: {e}")
        raise


def extract_images_from_zip(zip_path):
    """从zip文件中提取所有图片文件，返回图片数据和文件名的列表。"""
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")
    image_data_list = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取zip文件中的所有文件名
            file_list = zip_ref.namelist()
            
            # 过滤出图片文件并按自然顺序排序
            image_files = []
            for filename in file_list:
                # 跳过目录和隐藏文件
                if not filename.endswith('/') and not os.path.basename(filename).startswith('.'):
                    if filename.lower().endswith(valid_extensions):
                        image_files.append(filename)
            
            # 按自然顺序排序
            image_files = sorted(image_files, key=lambda x: natural_sort_key(os.path.basename(x)))
            
            if not image_files:
                print(f"在zip文件 {os.path.basename(zip_path)} 中未找到有效图片文件。")
                return []
            
            print(f"在zip文件中找到 {len(image_files)} 张图片")
            
            # 提取图片数据
            for filename in image_files:
                try:
                    with zip_ref.open(filename) as file:
                        image_data = file.read()
                        image_data_list.append((image_data, os.path.basename(filename)))
                except Exception as e:
                    print(f"提取图片 {filename} 时出错: {e}")
                    continue
                    
    except zipfile.BadZipFile:
        print(f"错误：{zip_path} 不是有效的zip文件")
        return []
    except Exception as e:
        print(f"读取zip文件 {zip_path} 时出错: {e}")
        return []
    
    return image_data_list


def merge_zip_images_to_pdf(zip_path, output_pdf_path):
    """将zip文件中的图片合并成PDF文件。"""
    # 从zip文件中提取图片数据
    image_data_list = extract_images_from_zip(zip_path)
    
    if not image_data_list:
        print(f"zip文件 {os.path.basename(zip_path)} 中没有可处理的图片。")
        return True  # 表示成功（没有图片需要处理）
    
    images_to_append = []
    first_image = None
    processed_image_objects = []  # 跟踪图片对象以便后续关闭
    
    try:
        print(f"正在处理zip文件 '{os.path.basename(zip_path)}' 中的图片...")
        
        # 处理图片数据
        for image_data, filename in tqdm(image_data_list, desc="处理图片", unit="张"):
            try:
                img = process_image_from_bytes(image_data, filename)
                processed_image_objects.append(img)
                if first_image is None:
                    first_image = img
                else:
                    images_to_append.append(img)
            except Exception:
                # 错误已在process_image_from_bytes中打印，停止处理此zip文件
                return False  # 表示失败
        
        if first_image:
            first_image.save(output_pdf_path, save_all=True, append_images=images_to_append)
            print(f"成功创建 PDF: {output_pdf_path}")
            return True  # 表示成功
        else:
            print(f"zip文件 {os.path.basename(zip_path)} 中没有可处理的图片。")
            return True  # 表示成功（没有图片处理）
            
    except Exception as e:
        print(f"创建 PDF {output_pdf_path} 时出错: {e}")
        return False  # 表示失败
    finally:
        # 确保所有打开的图片对象都被关闭
        for img in processed_image_objects:
            try:
                img.close()
            except Exception as close_err:
                print(f"关闭图片时出错: {close_err}")


def merge_images_to_pdf(folder_path, output_pdf_path):
    """Merges images in a folder into a single PDF file with natural sorting and progress."""
    image_files = []
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")
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
        # Process images
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
            return True # Indicate success
        else:
            print(f"文件夹 {folder_path} 中没有可处理的图片。")
            return True # Indicate success (no images processed)

    except Exception as e:
        print(f"创建 PDF {output_pdf_path} 时出错: {e}")
        return False # Indicate failure
    finally:
        # Ensure all opened image objects are closed
        for img in processed_image_objects:
            try:
                img.close()
            except Exception as close_err:
                print(f"关闭图片时出错: {close_err}")


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


def process_folders_sequentially(folders_to_process):
    """Processes a list of folders sequentially with progress tracking."""
    processed_count = 0
    total_folders = len(folders_to_process)
    print(f"\n准备顺序处理 {total_folders} 个文件夹...")

    for item_path, output_pdf_path, folder_name in tqdm(folders_to_process, desc="整体进度", unit="个文件夹"):
        try:
            success = merge_images_to_pdf(item_path, output_pdf_path)
            if success:
                processed_count += 1
                print(f"✓ 成功处理文件夹: {folder_name}")
            else:
                print(f"✗ 文件夹 '{folder_name}' 处理失败。")
        except Exception as exc:
            print(f"✗ 文件夹 '{folder_name}' 处理时产生严重错误: {exc}")

    return processed_count


def process_folders_concurrently(folders_to_process, max_workers):
    """Processes a list of folders concurrently using ProcessPoolExecutor and tqdm."""
    # 多进程保护 - 对于PyInstaller打包的exe文件必需
    if getattr(sys, 'frozen', False):
        # 在打包的exe中，需要设置multiprocessing的启动方法
        multiprocessing.set_start_method('spawn', force=True)
    
    processed_count = 0
    total_folders = len(folders_to_process)
    print(f"\n准备使用最多 {max_workers} 个进程并行处理 {total_folders} 个文件夹...")

    try:
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
                        processed_count += 1
                        print(f"✓ 成功处理文件夹: {folder_name}")
                    else:
                        print(f"✗ 文件夹 '{folder_name}' 处理失败或被中止。")
                except Exception as exc:
                    print(f"✗ 文件夹 '{folder_name}' 处理时产生严重错误: {exc}")
    except Exception as e:
        print(f"多进程处理时出错: {e}")
        print("正在切换到顺序处理模式...")
        # 如果多进程失败，回退到顺序处理
        processed_count = process_folders_sequentially(folders_to_process)

    return processed_count


def get_script_directory():
    """确定脚本所在的目录。"""
    if getattr(sys, 'frozen', False):
        # 打包的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 普通的.py文件
        return os.path.dirname(os.path.abspath(__file__))


def find_zip_files_to_process(base_dir):
    """在base_dir中查找需要处理的zip文件，跳过已存在对应PDF的文件。"""
    zip_files = []
    print(f"在 '{base_dir}' 中查找zip文件...")
    
    for item in os.listdir(base_dir):
        if item.lower().endswith('.zip'):
            zip_path = os.path.join(base_dir, item)
            if os.path.isfile(zip_path):
                # 生成对应的PDF文件名
                pdf_filename = f"{os.path.splitext(item)[0]}.pdf"
                output_pdf_path = os.path.join(base_dir, pdf_filename)
                
                if os.path.exists(output_pdf_path):
                    print(f"  - PDF 文件 '{pdf_filename}' 已存在，跳过zip文件 '{item}'。")
                    continue
                
                print(f"  + 找到待处理zip文件: {item}")
                zip_files.append((zip_path, output_pdf_path, item))
    
    return zip_files


def process_zip_files_sequentially(zip_files_to_process):
    """顺序处理zip文件列表，带进度跟踪。"""
    processed_count = 0
    total_files = len(zip_files_to_process)
    print(f"\n准备顺序处理 {total_files} 个zip文件...")
    
    for zip_path, output_pdf_path, zip_name in tqdm(zip_files_to_process, desc="整体进度", unit="个zip文件"):
        try:
            success = merge_zip_images_to_pdf(zip_path, output_pdf_path)
            if success:
                processed_count += 1
            else:
                print(f"zip文件 '{zip_name}' 处理失败。")
        except Exception as exc:
            print(f"zip文件 '{zip_name}' 处理时产生严重错误: {exc}")
    
    return processed_count


def process_single_folder():
    """处理单个文件夹的交互模式。"""
    print("\n=== 单个文件夹处理模式 ===")
    
    while True:
        folder_path = input("请输入文件夹的完整路径（或输入 'q' 退出）: ").strip()
        
        if folder_path.lower() == 'q':
            break
            
        if not os.path.exists(folder_path):
            print("错误：文件夹不存在，请重新输入。")
            continue
            
        if not os.path.isdir(folder_path):
            print("错误：请选择文件夹而不是文件。")
            continue
        
        # 生成输出PDF路径
        base_name = os.path.basename(folder_path)
        output_dir = os.path.dirname(folder_path)
        output_pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        
        # 检查PDF是否已存在
        if os.path.exists(output_pdf_path):
            overwrite = input(f"PDF文件 '{base_name}.pdf' 已存在，是否覆盖？(y/n): ").strip().lower()
            if overwrite != 'y':
                continue
        
        # 处理文件夹
        try:
            success = merge_images_to_pdf(folder_path, output_pdf_path)
            if success:
                print(f"✓ 成功处理文件夹: {os.path.basename(folder_path)}")
            else:
                print(f"✗ 处理文件夹失败: {os.path.basename(folder_path)}")
        except Exception as e:
            print(f"✗ 处理文件夹时出错: {e}")


def process_single_zip_file():
    """处理单个zip文件的交互模式。"""
    print("\n=== 单个zip文件处理模式 ===")
    
    while True:
        zip_path = input("请输入zip文件的完整路径（或输入 'q' 退出）: ").strip()
        
        if zip_path.lower() == 'q':
            break
            
        if not os.path.exists(zip_path):
            print("错误：文件不存在，请重新输入。")
            continue
            
        if not zip_path.lower().endswith('.zip'):
            print("错误：请选择zip文件。")
            continue
        
        # 生成输出PDF路径
        base_name = os.path.splitext(os.path.basename(zip_path))[0]
        output_dir = os.path.dirname(zip_path)
        output_pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        
        # 检查PDF是否已存在
        if os.path.exists(output_pdf_path):
            overwrite = input(f"PDF文件 '{base_name}.pdf' 已存在，是否覆盖？(y/n): ").strip().lower()
            if overwrite != 'y':
                continue
        
        # 处理zip文件
        try:
            success = merge_zip_images_to_pdf(zip_path, output_pdf_path)
            if success:
                print(f"✓ 成功处理zip文件: {os.path.basename(zip_path)}")
            else:
                print(f"✗ 处理zip文件失败: {os.path.basename(zip_path)}")
        except Exception as e:
            print(f"✗ 处理zip文件时出错: {e}")


def main():
    script_dir = get_script_directory()
    print(f"脚本运行目录: {script_dir}")
    print("\n=== 图片转PDF综合工具 4.0 ===")
    print("此工具支持多种图片源：zip压缩包、文件夹")
    
    # 选择处理模式
    print("\n请选择处理模式:")
    print("1. 批量处理当前目录下的所有zip文件")
    print("2. 处理单个指定的zip文件")
    print("3. 批量处理当前目录下的所有子文件夹（顺序处理）")
    print("4. 批量处理当前目录下的所有子文件夹（多进程并行）")
    print("5. 处理单个指定的文件夹")
    
    while True:
        choice = input("请输入选择 (1-5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            break
        print("无效选择，请输入 1-5 之间的数字")
    
    if choice == '1':
        # 批量处理zip文件
        zip_files_to_process = find_zip_files_to_process(script_dir)
        
        if not zip_files_to_process:
            print("\n未找到需要处理的新zip文件。")
        else:
            processed_count = process_zip_files_sequentially(zip_files_to_process)
            print(f"\n处理完成！成功处理了 {processed_count} 个zip文件。")
    
    elif choice == '2':
        # 单个zip文件处理模式
        process_single_zip_file()
    
    elif choice == '3':
        # 批量处理文件夹（顺序）
        folders_to_process = find_folders_to_process(script_dir)
        
        if not folders_to_process:
            print("\n未找到需要处理的新子文件夹。")
        else:
            processed_count = process_folders_sequentially(folders_to_process)
            print(f"\n处理完成！成功处理了 {processed_count} 个子文件夹。")
    
    elif choice == '4':
        # 批量处理文件夹（多进程）
        folders_to_process = find_folders_to_process(script_dir)
        
        if not folders_to_process:
            print("\n未找到需要处理的新子文件夹。")
        else:
            # 检查是否支持多进程
            try:
                # 设置多进程数量
                max_workers = max(1, (os.cpu_count() or 4) // 2)
                print(f"将使用 {max_workers} 个进程进行并行处理")
                print("注意：多进程模式可能需要更多内存，如果出现问题会自动切换到顺序处理模式")
                processed_count = process_folders_concurrently(folders_to_process, max_workers)
                print(f"\n处理完成！成功处理了 {processed_count} 个子文件夹。")
            except Exception as e:
                print(f"多进程模式启动失败: {e}")
                print("正在使用顺序处理模式...")
                processed_count = process_folders_sequentially(folders_to_process)
                print(f"\n处理完成！成功处理了 {processed_count} 个子文件夹。")
    
    else:  # choice == '5'
        # 单个文件夹处理模式
        process_single_folder()


if __name__ == "__main__":
    # 多进程保护 - 对于PyInstaller打包的exe文件和多进程必需
    multiprocessing.freeze_support()
    
    # 检查依赖库
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
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断。")
    except Exception as e:
        print(f"\n程序运行时出现错误: {e}")
    
    input("\n所有操作已完成。按 Enter 键退出...")