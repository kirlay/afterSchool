import tkinter as tk
from datetime import datetime

root = tk.Tk()

# 创建标签用于显示时间
time_label = tk.Label(root, text="", font=("Helvetica", 16))
time_label.pack()

def update_time():
    current_time = datetime.now().strftime('%H:%M:%S')
    time_label.config(text=current_time)
    # 每隔 1000 毫秒（1 秒）更新一次时间
    root.after(1000, update_time)

update_time()
root.mainloop()
