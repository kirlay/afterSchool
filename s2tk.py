import base64
import tkinter as tk
from PIL import Image, ImageTk

def display_image_from_string(image_string):
    # 将 base64 编码的字符串解码为字节数据
    image_data = base64.b64decode(image_string)
    # 使用 PIL 从字节数据创建 Image 对象
    img = Image.open(io.BytesIO(image_data))
    # 将 PIL Image 对象转换为 Tkinter 可用的 PhotoImage 对象
    photo = ImageTk.PhotoImage(img)
    # 创建一个标签来显示图片
    label = tk.Label(root, image=photo)
    label.image = photo  # 保持对 PhotoImage 对象的引用以防止垃圾回收
    label.pack()

root = tk.Tk()

# 这里使用一个示例字符串，实际应用中替换为你的字符串
image_string = "your_base64_encoded_image_string"
display_image_from_string(image_string)

root.mainloop()
