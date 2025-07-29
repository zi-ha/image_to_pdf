import os
import zipfile
import shutil
from PIL import Image, ImageOps
import sys
import re
from tqdm import tqdm
import io
import concurrent.futures
import multiprocessing


def natural_sort_key(s):
    """自然排序的键函数（例如：'image1.jpg', 'image2.jpg', 'image10.jpg'）"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', s)]


def get_target_size(images, size_mode="auto"):
    """
    根据所有图片计算目标尺寸
    size_mode: "auto" - 自动选择最常见的尺寸
              "max" - 使用最大尺寸
              "min" - 使用最小尺寸
              (width, height) - 指定尺寸
    """
    if isinstance(size_mode, tuple):
        return size_mode
    
    sizes = [img.size for img in images]
    
    if size_mode == "max":
        max_width = max(size[0] for size in sizes)
        max_height = max(size[1] for size in sizes)
        return (max_width, max_height)
    elif size_mode == "min":
        min_width = min(size[0] for size in sizes)
        min_height = min(size[1] for size in sizes)
        return (min_width, min_height)
    else:  # auto - 选择最常见的尺寸
        size_counts = {}
        for size in sizes:
            size_counts[size] = size_counts.get(size, 0) + 1
        
        # 如果有相同尺寸的图片，选择最常见的
        if size_counts:
            most_common_size = max(size_counts.items(), key=lambda x: x[1])[0]
            return most_common_size
        
        # 否则使用第一张图片的尺寸
        return sizes[0] if sizes else (1920, 1080)


def resize_image_uniform(img, target_size, resize_method="fit"):
    """
    将图片调整到统一尺寸
    resize_method: 
        "fit" - 等比例缩放，保持宽高比，可能有黑边
        "fill" - 等比例缩放并裁剪，填满目标尺寸
        "stretch" - 拉伸到目标尺寸，可能变形
    """
    if resize_method == "fit":
        # 等比例缩放，保持宽高比，添加黑边
        img_resized = ImageOps.pad(img, target_size, color=(255, 255, 255))  # 白色背景
        return img_resized
    
    elif resize_method == "fill":
        # 等比例缩放并裁剪，填满目标尺寸
        img_resized = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
        return img_resized
    
    elif resize_method == "stretch":
        # 直接拉伸到目标尺寸
        img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
        return img_resized
    
    else:
        return img


def process_image_from_path(image_path, target_size=None, resize_method="fit"):
    """从文件路径处理图片，返回RGB格式的图片对象"""
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 如果指定了目标尺寸，进行尺寸调整
        if target_size:
            img = resize_image_uniform(img, target_size, resize_method)
        
        return img
    except Exception as e:
        print(f"错误：无法处理图片 {image_path}: {e}")
        raise


def process_image_from_bytes(image_data, filename, target_size=None, resize_method="fit"):
    """从字节数据处理图片，返回RGB格式的图片对象"""
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 如果指定了目标尺寸，进行尺寸调整
        if target_size:
            img = resize_image_uniform(img, target_size, resize_method)
        
        return img
    except Exception as e:
        print(f"错误：无法处理图片 {filename}: {e}")
        raise


def merge_images_to_pdf_from_folder(folder_path, output_pdf_path, uniform_size=True, resize_method="fit"):
    """将文件夹中的图片合并成PDF"""
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")
    image_files = []
    
    try:
        filenames = sorted(os.listdir(folder_path), key=natural_sort_key)
        for filename in filenames:
            if filename.lower().endswith(valid_extensions):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    image_files.append(file_path)
    except Exception as e:
        print(f"读取文件夹 {folder_path} 时出错: {e}")
        return False

    if not image_files:
        print(f"文件夹 {folder_path} 中未找到图片文件")
        return True

    try:
        # 如果需要统一尺寸，先加载所有图片获取目标尺寸
        target_size = None
        if uniform_size:
            print(f"正在分析图片尺寸...")
            temp_images = []
            for image_path in image_files[:10]:  # 只分析前10张图片来确定尺寸
                try:
                    img = Image.open(image_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    temp_images.append(img)
                except:
                    continue
            
            if temp_images:
                target_size = get_target_size(temp_images, "auto")
                print(f"目标尺寸: {target_size[0]}x{target_size[1]}")
                
                # 关闭临时图片
                for img in temp_images:
                    img.close()
        
        # 处理所有图片
        images = []
        print(f"正在处理 {len(image_files)} 张图片...")
        for image_path in tqdm(image_files, desc="处理图片", unit="张"):
            img = process_image_from_path(image_path, target_size, resize_method)
            images.append(img)
        
        if images:
            images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
            # 关闭所有图片对象
            for img in images:
                img.close()
            return True
    except Exception as e:
        print(f"创建PDF {output_pdf_path} 时出错: {e}")
        return False


def merge_images_to_pdf_from_zip(zip_path, output_pdf_path, uniform_size=True, resize_method="fit"):
    """将zip文件中的图片合并成PDF"""
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            image_files = []
            
            for filename in file_list:
                if (not filename.endswith('/') and 
                    not os.path.basename(filename).startswith('.') and
                    filename.lower().endswith(valid_extensions)):
                    image_files.append(filename)
            
            image_files = sorted(image_files, key=lambda x: natural_sort_key(os.path.basename(x)))
            
            if not image_files:
                print(f"zip文件 {os.path.basename(zip_path)} 中未找到图片文件")
                return True
            
            # 如果需要统一尺寸，先分析部分图片获取目标尺寸
            target_size = None
            if uniform_size:
                print(f"正在分析图片尺寸...")
                temp_images = []
                for filename in image_files[:10]:  # 只分析前10张图片
                    try:
                        with zip_ref.open(filename) as file:
                            image_data = file.read()
                            img = Image.open(io.BytesIO(image_data))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            temp_images.append(img)
                    except:
                        continue
                
                if temp_images:
                    target_size = get_target_size(temp_images, "auto")
                    print(f"目标尺寸: {target_size[0]}x{target_size[1]}")
                    
                    # 关闭临时图片
                    for img in temp_images:
                        img.close()
            
            # 处理所有图片
            images = []
            print(f"正在处理 {len(image_files)} 张图片...")
            for filename in tqdm(image_files, desc="处理图片", unit="张"):
                with zip_ref.open(filename) as file:
                    image_data = file.read()
                    img = process_image_from_bytes(image_data, os.path.basename(filename), target_size, resize_method)
                    images.append(img)
            
            if images:
                images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
                # 关闭所有图片对象
                for img in images:
                    img.close()
                return True
                
    except Exception as e:
        print(f"处理zip文件 {zip_path} 时出错: {e}")
        return False


def find_items_to_process(base_dir):
    """查找需要处理的zip文件和文件夹"""
    items = []
    skipped_folders = ['build', 'dist', '__pycache__', '.git', '.vscode']
    
    print(f"在 '{base_dir}' 中查找zip文件和文件夹...")
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        # 处理zip文件
        if item.lower().endswith('.zip') and os.path.isfile(item_path):
            pdf_name = f"{os.path.splitext(item)[0]}.pdf"
            output_pdf_path = os.path.join(base_dir, pdf_name)
            
            if os.path.exists(output_pdf_path):
                print(f"  - 跳过（PDF已存在）: {item}")
                continue
            
            print(f"  + 找到zip文件: {item}")
            items.append(('zip', item_path, output_pdf_path, item))
        
        # 处理文件夹
        elif os.path.isdir(item_path):
            if item.lower() in skipped_folders:
                print(f"  - 跳过系统文件夹: {item}")
                continue
            
            pdf_name = f"{item}.pdf"
            output_pdf_path = os.path.join(base_dir, pdf_name)
            
            if os.path.exists(output_pdf_path):
                print(f"  - 跳过（PDF已存在）: {item}")
                continue
            
            print(f"  + 找到文件夹: {item}")
            items.append(('folder', item_path, output_pdf_path, item))
    
    return items


def process_single_item(item_info, uniform_size=True, resize_method="fit"):
    """处理单个项目（zip文件或文件夹）"""
    item_type, item_path, output_pdf_path, item_name = item_info
    
    try:
        if item_type == 'zip':
            success = merge_images_to_pdf_from_zip(item_path, output_pdf_path, uniform_size, resize_method)
        else:  # folder
            success = merge_images_to_pdf_from_folder(item_path, output_pdf_path, uniform_size, resize_method)
        
        if success:
            print(f"✓ 成功处理: {item_name}")
            return True
        else:
            print(f"✗ 处理失败: {item_name}")
            return False
    except Exception as e:
        print(f"✗ 处理 {item_name} 时出错: {e}")
        return False


def process_items_with_multiprocessing(items, max_workers, uniform_size=True, resize_method="fit"):
    """使用多进程处理项目列表"""
    if getattr(sys, 'frozen', False):
        multiprocessing.set_start_method('spawn', force=True)
    
    processed_count = 0
    total_items = len(items)
    
    print(f"\n使用 {max_workers} 个进程并行处理 {total_items} 个项目...")
    
    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(process_single_item, item, uniform_size, resize_method): item[3] 
                             for item in items}
            
            for future in tqdm(concurrent.futures.as_completed(future_to_item), 
                             total=total_items, desc="处理进度", unit="项"):
                item_name = future_to_item[future]
                try:
                    if future.result():
                        processed_count += 1
                except Exception as exc:
                    print(f"✗ {item_name} 处理时出现异常: {exc}")
    
    except Exception as e:
        print(f"多进程处理失败: {e}")
        print("切换到单进程模式...")
        # 回退到单进程处理
        for item in tqdm(items, desc="处理进度", unit="项"):
            if process_single_item(item, uniform_size, resize_method):
                processed_count += 1
    
    return processed_count


def get_script_directory():
    """获取脚本所在目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def main():
    """主函数 - 增强版本，支持尺寸统一"""
    script_dir = get_script_directory()
    print("=== 图片转PDF工具 5.1 (尺寸统一版) ===")
    print(f"工作目录: {script_dir}")
    print("自动扫描并处理当前目录下的zip文件和文件夹")
    print("支持图片尺寸统一功能\n")
    
    # 查找需要处理的项目
    items_to_process = find_items_to_process(script_dir)
    
    if not items_to_process:
        print("未找到需要处理的新项目（zip文件或文件夹）")
        return
    
    # 显示找到的项目
    print(f"\n找到 {len(items_to_process)} 个项目需要处理:")
    for item_type, _, _, item_name in items_to_process:
        print(f"  - {item_type}: {item_name}")
    
    # 尺寸统一设置
    print(f"\n=== 尺寸统一设置 ===")
    print("1. 启用尺寸统一（推荐）")
    print("2. 保持原始尺寸")
    
    uniform_choice = input("请选择 (1-2，默认1): ").strip()
    uniform_size = uniform_choice != '2'
    
    resize_method = "fit"
    if uniform_size:
        print(f"\n=== 尺寸调整方式 ===")
        print("1. 等比例缩放 + 白边填充（推荐，不变形）")
        print("2. 等比例缩放 + 裁剪（填满页面，可能裁掉部分内容）")
        print("3. 拉伸（可能变形）")
        
        method_choice = input("请选择调整方式 (1-3，默认1): ").strip()
        if method_choice == '2':
            resize_method = "fill"
        elif method_choice == '3':
            resize_method = "stretch"
        else:
            resize_method = "fit"
        
        method_names = {"fit": "等比例缩放+填充", "fill": "等比例缩放+裁剪", "stretch": "拉伸"}
        print(f"已选择: {method_names[resize_method]}")
    
    # 确认处理
    confirm = input(f"\n是否开始处理这 {len(items_to_process)} 个项目？(y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        return
    
    # 设置多进程数量（使用CPU核心数的一半，最少1个）
    max_workers = max(1, (os.cpu_count() or 4) // 2)
    
    # 开始处理
    processed_count = process_items_with_multiprocessing(items_to_process, max_workers, uniform_size, resize_method)
    
    print(f"\n处理完成！")
    print(f"成功处理: {processed_count}/{len(items_to_process)} 个项目")
    if uniform_size:
        print(f"所有图片已统一尺寸（方式: {method_names.get(resize_method, resize_method)}）")


if __name__ == "__main__":
    # 多进程保护
    multiprocessing.freeze_support()
    
    # 检查依赖库
    missing_libs = []
    try:
        from PIL import Image, ImageOps
    except ImportError:
        missing_libs.append("Pillow")
    try:
        from tqdm import tqdm
    except ImportError:
        missing_libs.append("tqdm")
    
    if missing_libs:
        print("错误：缺少必要的库:", ", ".join(missing_libs))
        print("请使用以下命令安装:")
        for lib in missing_libs:
            print(f"  pip install {lib}")
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行时出现错误: {e}")
    
    input("\n按 Enter 键退出...")