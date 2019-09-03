// 裁剪图片、训练的状态
export const taskStatus = [
  { 'id': 0, 'status': '初始化 ', 'type': 'info' },
  { 'id': 1, 'status': '送去处理', 'type': 'info' },
  { 'id': 2, 'status': '开始处理', 'type': 'info' },
  { 'id': 3, 'status': '处理出错', 'type': 'danger' },
  { 'id': 4, 'status': '处理完成', 'type': 'success' },
  { 'id': 5, 'status': '目录不存在', 'type': 'danger' },
  { 'id': 6, 'status': '开始训练', 'type': 'info' },
  { 'id': 7, 'status': '训练出错', 'type': 'danger' },
  { 'id': 8, 'status': '训练完成', 'type': '' }
]

// 标注页面把原图的宽缩放到几个像素点（原图太大了一个屏幕显示不过来）
export const page3ImgWidth = 645