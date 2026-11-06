import base64

# 读取图片文件
with open('xh.ico', 'rb') as image_file:
    # 将图片编码为 base64 字符串
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

# 将编码后的字符串写入 txt 文件
with open('image_as_string.txt', 'w') as txt_file:
    txt_file.write(encoded_string)
