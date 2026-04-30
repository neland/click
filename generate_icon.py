"""生成鼠标形状的软件图标"""

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess, sys
    print("Pillow 未安装，正在自动安装...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw


def create_mouse_icon(output_path="icon.ico"):
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        s = size

        # 鼠标指针多边形顶点（相对坐标）
        points = [
            (s * 0.28, s * 0.12),  # 尖端
            (s * 0.40, s * 0.50),  # 右肩上
            (s * 0.33, s * 0.50),  # 右肩内
            (s * 0.42, s * 0.72),  # 右下外（尾巴）
            (s * 0.32, s * 0.70),  # 右下内
            (s * 0.26, s * 0.52),  # 底部右
            (s * 0.18, s * 0.52),  # 底部左
        ]

        # 阴影层（偏移 1px，深灰色）
        shadow_points = [(x + 1, y + 1) for x, y in points]
        draw.polygon(shadow_points, fill=(30, 30, 30, 200))

        # 主体层（白色箭头）
        draw.polygon(points, fill=(240, 240, 240, 255), outline=(20, 20, 20, 255))

        images.append(img)

    # 保存为包含多尺寸的 ICO 文件
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes]
    )
    print(f"图标已生成: {output_path}")


if __name__ == "__main__":
    create_mouse_icon()
