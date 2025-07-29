import os
from PIL import Image
from fpdf import FPDF
import natsort
import argparse

def merge_images_to_pdf(main_folder):
    print(f"开始处理文件夹: {main_folder}")
    # 确保主文件夹存在
    if not os.path.isdir(main_folder):
        print(f"错误：文件夹 {main_folder} 不存在或不是一个有效的目录。")
        return

    # 遍历主文件夹下的所有项目
    for item_name in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, item_name)

        # 检查是否是子文件夹
        if os.path.isdir(subfolder_path):
            print(f"  正在处理子文件夹: {item_name}")
            image_files = []
            # 遍历子文件夹中的文件
            for filename in os.listdir(subfolder_path):
                # 检查是否是图片文件 (增加支持 .gif, .bmp, .tiff, .webp)
                supported_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp')
                if filename.lower().endswith(supported_extensions):
                    image_files.append(os.path.join(subfolder_path, filename))

            if not image_files:
                print(f"    子文件夹 {item_name} 中没有找到支持的图片文件，跳过。")
                continue

            # 使用 natsort 进行自然排序
            image_files = natsort.natsorted(image_files)
            print(f"    找到 {len(image_files)} 张图片，已排序。")

            # 创建 PDF 对象
            pdf = FPDF()
            pdf_output_path = os.path.join(main_folder, f"{item_name}.pdf")
            first_image_processed = False
            target_width_pt = 0

            try:
                print(f"    开始为 {item_name} 创建 PDF...")
                # 遍历排序后的图片文件并添加到 PDF
                for i, image_path in enumerate(image_files):
                    try:
                        with Image.open(image_path) as img:
                            # 尝试处理 RGBA 或 P 模式（带透明度）的图片，转换为 RGB
                            if img.mode in ('RGBA', 'P'):
                                print(f"      转换图片 {os.path.basename(image_path)} 从 {img.mode} 到 RGB")
                                img = img.convert('RGB')

                            width, height = img.size
                            width_pt, height_pt = width, height # FPDF 似乎可以直接使用像素值

                            if not first_image_processed:
                                target_width_pt = width_pt # 以第一张图片的宽度为基准
                                print(f"      设置基准宽度为: {target_width_pt} pt (来自 {os.path.basename(image_path)})")
                                first_image_processed = True

                            # 计算调整后的尺寸以匹配目标宽度，保持纵横比
                            if width_pt != target_width_pt:
                                aspect_ratio = height / width
                                adjusted_height_pt = int(target_width_pt * aspect_ratio)
                                adjusted_width_pt = target_width_pt
                                print(f"      调整图片 {os.path.basename(image_path)} 尺寸: {width_pt}x{height_pt} -> {adjusted_width_pt}x{adjusted_height_pt}")
                            else:
                                adjusted_width_pt = width_pt
                                adjusted_height_pt = height_pt

                            # 添加页面，尺寸根据调整后的图片确定
                            pdf.add_page(format=(adjusted_width_pt, adjusted_height_pt))
                            # 将图片添加到页面，使用调整后的尺寸
                            # 保存临时文件以兼容 fpdf 对非 jpg 格式的处理
                            temp_img_path = None
                            if not image_path.lower().endswith('.jpg'):
                                temp_img_path = os.path.join(subfolder_path, f"temp_img_for_pdf_{i}.jpg")
                                img.save(temp_img_path, 'JPEG')
                                pdf.image(temp_img_path, 0, 0, adjusted_width_pt, adjusted_height_pt)
                                os.remove(temp_img_path) # 删除临时文件
                            else:
                                pdf.image(image_path, 0, 0, adjusted_width_pt, adjusted_height_pt)

                    except Exception as img_err:
                        print(f"      处理图片 {os.path.basename(image_path)} 时出错: {img_err}")

                # 保存 PDF 文件
                if pdf.page_no() > 0:
                    pdf.output(pdf_output_path, "F")
                    print(f"    成功创建 PDF: {pdf_output_path} ({pdf.page_no()} 页)")
                else:
                    print(f"    未能添加任何页面到 PDF {pdf_output_path}，跳过保存。")

            except Exception as pdf_err:
                print(f"    创建 PDF 文件 {pdf_output_path} 时出错: {pdf_err}")

    print("处理完成。")

if __name__ == "__main__":
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='将指定文件夹内每个子文件夹中的图片合并成一个 PDF 文件。')
    parser.add_argument('folder', type=str, nargs='?', default='.', 
                        help='包含子文件夹的主文件夹路径。如果未提供，则默认为当前目录。')
    
    args = parser.parse_args()
    
    # 获取绝对路径
    target_folder = os.path.abspath(args.folder)
    
    print(f"目标文件夹: {target_folder}")
    merge_images_to_pdf(target_folder)
