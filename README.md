# 漫画图片转PDF工具

## 项目简介

这是一个Python脚本，用于将文件夹中的漫画图片自动合并为PDF文件。支持JPG、PNG、BMP、GIF和TIFF格式，并按自然顺序排序文件名（如image1.jpg, image2.jpg, ..., image10.jpg）。

## 功能特点

- 自动扫描子文件夹中的图片文件
- 支持多种常见图片格式
- 文件名自然排序
- 自动跳过已处理的文件夹
- 显示处理进度条

## 使用说明

1. 将脚本`image_to_pdf.py`放在包含漫画文件夹的目录中
2. 每个子文件夹应该包含一个漫画章节的所有图片
3. 运行脚本：`python image_to_pdf.py`
4. 脚本会自动为每个子文件夹生成对应的PDF文件

## 依赖安装

运行前请确保安装以下Python库：

```bash
pip install Pillow tqdm
```
打包命令 pyinstaller --onefile --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy --exclude-module pandas --exclude-module scipy --exclude-module PyQt5 --exclude-module wx --add-data d:\Desktop\漫画\漫画.ico:. --icon d:\Desktop\漫画\漫画.ico --name 漫画转PDF工具 d:\Desktop\漫画\image_to_pdf.py
## 文件结构建议

文件组织方式如下：

```
漫画根目录/
  ├── 300/          # 章节300
  │   ├── 0001.jpg  # 建议使用4位数字命名
  │   ├── 0002.jpg
  │   └── ...
  ├── 301/          # 章节301
  │   ├── 0001.jpg
  │   ├── 0002.jpg
  │   └── ...
  └── 300.pdf       # 自动生成的PDF
  └──脚本/程序       # 
```

## 注意事项

- 图片文件名建议使用数字序号命名（如0001.jpg, 0002.jpg等）
- 脚本会自动跳过特殊文件夹（如build, dist等）
- 如果PDF已存在，会跳过该文件夹
- 处理过程中会显示进度条

## 输出

生成的PDF文件会放在与图片文件夹相同的目录中，文件名与文件夹名相同（如`300\`文件夹会生成`300.pdf`）
