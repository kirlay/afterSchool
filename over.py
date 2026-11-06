import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import base64
import ico
import io
import tempfile
import os

#6个年级
n=['一','二','三','四','五','六']
#每个年级4个班
c=[4,4,4,4,4,4]

wd=tk.Tk()

#wd.overrideredirect(True)
wd.configure(bg='black')
wd.geometry('548x416+0+-30')
#设置窗口锁定缩放
wd.resizable(width=False,height=False)

#插入图片
image_data = base64.b64decode(ico.big_string)
    # 使用 PIL 从字节数据创建 Image 对象
img = Image.open(io.BytesIO(image_data))
    # 将 PIL Image 对象转换为 Tkinter 可用的 PhotoImage 对象
resized_img = img.resize((60, 60), Image.LANCZOS)
photo = ImageTk.PhotoImage(resized_img)
    # 创建一个标签来显示图片
l_image=tk.Label(wd, image=photo,bg='black')
l_image.image=photo
l_image.place(x=40,y=8)

# 设置窗口图标
wd.title("放学了吗？")
try:
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, 'temp.ico')
    img.save(temp_file_path, format='ICO')
    wd.iconbitmap(temp_file_path)
except Exception as e:
    # 处理获取临时目录失败的情况
    print(f"无法获取临时目录，错误：{e}")
    img.save('temp.ico', format='ICO')
    wd.iconbitmap('temp.ico')

'''
# 设置窗口关闭时执行的函数
def cls():
    print("关闭时间：",datetime.datetime.now())
    wd.destroy()
wd.protocol(name="WM_DELETE_WINDOW",func=cls)
'''
tk.Label(wd,text='宁波市四眼碶小学樱花校区\n放学情况', font=('黑体',20),bg='black',fg='#f26522').place(x=140,y=12)
def ini():
    cnt=0
    for i in range(0,6):
        for j in range(1,c[i]+1):
            px=30+123*(int(j)-1)
            py=95+44*(int(i))
            l=tk.Label(wd,text=f'{n[int(i)]}{j}班', font=('黑体',16),bg='black',foreground="green")
            l.place(x=px,y=py)
            labels.append(l)
            m[f'{int(i)+1}0{j}']=(cnt,i,j)
            cnt+=1

    
labels = []
m={}
ini()
#print(m)
def handle_enter(event):
    # 获取Entry小部件的内容
    value = entry.get()
    entry_var.set("")
    entry.focus_set()
    if value in m:
        labels[m[value][0]].config(text=f'{n[int(m[value][1])]}{m[value][2]}班放学',fg="red")
    elif value[0]=='-':
        value=value[1:]
        if value in m:
            labels[m[value][0]].config(text=f'{n[int(m[value][1])]}{m[value][2]}班',fg="green")
    elif value=='000':
        result = messagebox.askyesno("确认操作", "是否将所有班级设置成“未放学”的状态？")
        if result:
            reset_function()

        
        
            
#在enytry里面输入102，然后回车，就表示102放学；如果输入-102，表示撤销102放学
tk.Label(wd,text='读取班级编号：', font=('黑体',12),bg='black',fg="green").place(x=20,y=360)
entry_var = tk.StringVar()
entry=tk.Entry(wd,textvariable=entry_var,width=15)
entry.place(x=150,y=360)
entry.focus_set()
entry.bind('<Return>', handle_enter)

def reset_function():
    i=0
    for key in m:
      labels[i].config(text=f'{n[int(m[key][1])]}{m[key][2]}班',foreground="green")
      i=i+1
            
#reset_button = tk.Button(wd, text="复位", command=reset_function)
#reset_button.place(x=300,y=355)

#在14：50还原 在16：25最小化
time_str_begin = '14:50:00'
time_str_end = '16:25:00'
def check_time():
    current_time = datetime.datetime.now()
# 提取时、分、秒部分并格式化为字符串
    current_time_str = f"{current_time.hour:02d}:{current_time.minute:02d}:{current_time.second:02d}"
    if current_time_str > time_str_begin and current_time_str < time_str_end :
        wd.deiconify()
        entry.focus_set()
    else:
        wd.iconify()
        reset_function()
        
    t=300000
    if (current_time_str > "17:00:00" and current_time_str < "24:00:00" )or (current_time_str > "00:00:00" and current_time_str < "13:00:00" ):
        t=1000*60*60 #1小时检测一次
    wd.after(t,check_time)#300秒检测一次
check_time()
#按F1弹出帮助信息
def show_help():
    help_window = tk.Toplevel()
    help_window.title("帮助信息")
    label = tk.Label(help_window, text="#################################################\n"+"#如果输入102，然后回车，就表示102放学；                                    #\n"+"#如果输入-102，然后回车，表示撤销102放学；                                #\n"+"#如果输入000，然后回车，表示将所有班级设置成“未放学”的状态。      #\n"+"#谢谢您的使用！                                                                          #\n"+"#                软件设计：严科磊                                                       #\n"+"#            联系电话：13777145451                                                 #\n"+"#################################################\n", justify=tk.LEFT)
    label.pack()
    tk.Button(help_window,text="将所有班级设置成“未放学”的状态", command=reset_function).pack()


wd.bind('<F1>', lambda event: show_help())

wd.mainloop()
