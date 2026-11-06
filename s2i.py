import base64
import ico
import io
import tkinter as tk
from PIL import Image, ImageTk
wd = tk.Tk()
# 将 base64 编码的字符串解码为字节数据
image_data = base64.b64decode(ico.big_string)
    # 使用 PIL 从字节数据创建 Image 对象
img = Image.open(io.BytesIO(image_data))
    # 将 PIL Image 对象转换为 Tkinter 可用的 PhotoImage 对象
photo = ImageTk.PhotoImage(img)
    # 创建一个标签来显示图片
label = tk.Label(wd, image=photo)
label.image = photo  # 保持对 PhotoImage 对象的引用以防止垃圾回收
label.pack()
