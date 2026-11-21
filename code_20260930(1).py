import tkinter as tk
import random
import time
import math
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk, ImageOps
except ImportError:
    Image = ImageDraw = ImageFilter = ImageFont = ImageTk = ImageOps = None

hearts, all_wins = [], []
tips = ['学业有成', '好好爱自己', '好好吃饭',
        '身体健康', '顺顺利利', '别熬夜', '天凉了多穿衣服']
# 卡片外观：底色 + 文字颜色
PALETTE = [
    ('#ffc9da', '#a8365a'),   # 樱花粉
    ('#c2e5f5', '#2c6e8c'),   # 天空蓝
    ('#ffe6a8', '#9a6a14'),   # 奶油黄
    ('#e3d0f7', '#6a4a93'),   # 薰衣草
    ('#d6eccb', '#4a7a45'),   # 薄荷绿
]
CARD_W, CARD_H = 150, 60              # 卡片尺寸
CARD_R = 16                           # 圆角半径
KEY_COLOR = '#ff00ff'                 # 卡片圆角外要抠成透明的颜色
FONT_PX = 17                          # 正文字号
HEART_PX = 15                         # 卡片上小爱心的字号
USE_CARDS = False                     # 系统支持透明色时用圆角卡片
card_cache, font_cache = {}, {}

# 贺卡
GREET_W, GREET_H = 470, 610
GREET_LINES = ['愿你的每一岁都奔走在热爱里，',
               '愿所有的美好都如约而至，',
               '岁岁平安，年年欢喜。']
GREET_SIGN = '—— 生日快乐，不止今天'

# 3D 蛋糕：按 2 倍尺寸画再缩小，边缘才平滑
CAKE_W, CAKE_H = 560, 620
CAKE_S = 2
CAKE_FRAMES = 24                      # 转一圈用多少帧
CAKE_SECONDS = 13                     # 蛋糕停留时间

root = None
bg_photo = None
bg_image = None
cake_cache = {}

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE_NAME = '2ccc4cfcc9236a3ed50be5b38939d263.jpg'   # 同目录下的背景图
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')


def heart_points(n, screen_w, screen_h):
    points = []
    for i in range(n):
        t = i / n * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        sx = int(screen_w / 2 + x * 20 - 50)
        sy = int(screen_h / 2 - y * 20 - 80)
        sx = max(0, min(sx, screen_w - CARD_W))
        sy = max(0, min(sy, screen_h - CARD_H))
        points.append([sx, sy])
    return points


def close_all(event=None):
    for w in hearts + all_wins:
        try:
            if isinstance(w, tk.Toplevel) and w.winfo_exists():
                w.destroy()
        except tk.TclError:
            pass
    try:
        if root is not None and root.winfo_exists():
            root.destroy()
    except tk.TclError:
        pass
    os._exit(0)          # 直接结束进程，所有窗口跟着消失


def find_image():
    """找背景图：优先用指定文件名，找不到就用目录里第一张图片。"""
    path = os.path.join(HERE, IMAGE_NAME)
    if os.path.isfile(path):
        return path
    try:
        for name in sorted(os.listdir(HERE)):
            if name.lower().endswith(IMAGE_EXTS):
                return os.path.join(HERE, name)
    except OSError:
        pass
    return None


def show_background(screen_w, screen_h):
    """把图片等比缩放并居中裁切，铺满整个屏幕作为背景。"""
    global bg_photo, bg_image
    frame = tk.Frame(root, bd=0, highlightthickness=0, bg='#ffe6ee')
    frame.place(x=0, y=0, width=screen_w, height=screen_h)

    path = find_image()
    if path and Image is not None:
        try:
            with Image.open(path) as im:
                img = ImageOps.fit(im.convert('RGB'),
                                   (screen_w, screen_h), Image.LANCZOS)
            bg_photo = ImageTk.PhotoImage(img)
            bg_image = img               # 贺卡和蛋糕要从这张图上裁背景
            label = tk.Label(frame, image=bg_photo, bd=0,
                             highlightthickness=0, bg='#ffe6ee')
            label.place(x=0, y=0, width=screen_w, height=screen_h)
            label.bind('<Escape>', close_all)
            return frame
        except Exception as exc:      # 图片损坏、格式不支持等情况
            print('背景图片加载失败：%s' % exc)
    elif path and Image is None:
        print('想用图片做背景，请先安装 Pillow：pip install pillow')

    # 没有图片或没装 Pillow 时，用一块淡粉背景兜底
    tk.Label(frame, text='生日快乐', font=('微软雅黑', 72, 'bold'),
             fg='#ff7fae', bg='#ffe6ee').place(x=0, y=0,
                                              width=screen_w, height=screen_h)
    return frame


def card_font(kind='text'):
    """取字体：正文用微软雅黑粗体，小爱心用带 ♥ 的 Segoe UI Symbol。"""
    if kind not in font_cache:
        if kind == 'heart':
            names, size = ('seguisym.ttf',), HEART_PX
        else:
            names, size = ('msyhbd.ttc', 'msyh.ttc', 'simhei.ttf'), FONT_PX
        font = None
        for name in names:
            try:
                font = ImageFont.truetype(name, size)
                break
            except (OSError, IOError):
                continue
        if font is None and kind == 'text':
            font = ImageFont.load_default()
        font_cache[kind] = font
    return font_cache[kind]


def rounded_rect(draw, box, radius, fill):
    """画一个实心圆角矩形（兼容没有 rounded_rectangle 的旧版 Pillow）。"""
    x0, y0, x1, y1 = box
    r = radius
    draw.rectangle((x0 + r, y0, x1 - r, y1), fill=fill)
    draw.rectangle((x0, y0 + r, x1, y1 - r), fill=fill)
    draw.pieslice((x0, y0, x0 + 2 * r, y0 + 2 * r), 180, 270, fill=fill)
    draw.pieslice((x1 - 2 * r, y0, x1, y0 + 2 * r), 270, 360, fill=fill)
    draw.pieslice((x0, y1 - 2 * r, x0 + 2 * r, y1), 90, 180, fill=fill)
    draw.pieslice((x1 - 2 * r, y1 - 2 * r, x1, y1), 0, 90, fill=fill)


def card_image(text, fill, ink):
    """画一张卡片：白色描边 + 圆角 + 前面一个小爱心。"""
    img = Image.new('RGB', (CARD_W, CARD_H), KEY_COLOR)
    draw = ImageDraw.Draw(img)
    rounded_rect(draw, (0, 0, CARD_W - 1, CARD_H - 1), CARD_R, 'white')
    rounded_rect(draw, (2, 2, CARD_W - 3, CARD_H - 3), CARD_R - 2, fill)

    font = card_font('text')
    text_w, text_h = font.getmask(text).size
    left = (CARD_W - text_w) // 2
    top = (CARD_H - text_h) // 2

    heart_font = card_font('heart')
    if heart_font is not None:
        heart = '♥'
        heart_w, heart_h = heart_font.getmask(heart).size
        gap = 6
        left = (CARD_W - (heart_w + gap + text_w)) // 2
        draw.text((left, top + (text_h - heart_h) // 2), heart,
                  font=heart_font, fill=ink)
        left += heart_w + gap

    draw.text((left, top), text, font=font, fill=ink)
    return img


def card_photo(text, fill, ink):
    """同样的卡片只画一次，之后重复使用。"""
    key = (text, fill, ink)
    photo = card_cache.get(key)
    if photo is None:
        photo = ImageTk.PhotoImage(card_image(text, fill, ink))
        card_cache[key] = photo
    return photo


def cards_supported():
    """检查系统能不能把某个颜色设成透明（圆角卡片需要）。"""
    probe = tk.Toplevel(root)
    probe.withdraw()
    try:
        probe.attributes('-transparentcolor', KEY_COLOR)
        return True
    except tk.TclError:
        return False
    finally:
        probe.destroy()


def create_popup(x, y):
    win = tk.Toplevel()
    win.overrideredirect(True)      # 去掉标题栏，右上角的叉叉也就没了
    win.geometry(f'{CARD_W}x{CARD_H}+{x}+{y}')
    win.attributes('-topmost', 1)
    text = random.choice(tips)
    fill, ink = random.choice(PALETTE)

    if USE_CARDS:
        win.configure(bg=KEY_COLOR)
        tk.Label(win, image=card_photo(text, fill, ink),
                 bd=0, bg=KEY_COLOR).place(
            x=0, y=0, relwidth=1, relheight=1)
        win.attributes('-transparentcolor', KEY_COLOR)
    else:                           # 不支持透明色就用普通色块
        win.configure(bg=fill)
        tk.Label(win, text=text, bg=fill, fg=ink,
                 font=('微软雅黑', 14, 'bold')).place(
            x=0, y=0, relwidth=1, relheight=1)
    win.bind('<Escape>', close_all)
    return win


def hex2rgb(color):
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def shade(color, k):
    return tuple(min(255, int(c * k)) for c in color)


def load_font(names, size, fallback=True):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default() if fallback else None


def background_slice(x, y, w, h):
    """从背景图上裁一块：贺卡和蛋糕贴在上面，接缝就看不出来。"""
    if bg_image is not None:
        return bg_image.crop((x, y, x + w, y + h)).convert('RGBA')
    return Image.new('RGBA', (w, h), hex2rgb('#ffe6ee') + (255,))


def draw_heart(draw, cx, cy, r, fill):
    draw.ellipse((cx - r, cy - r * 0.9, cx, cy + r * 0.1), fill=fill)
    draw.ellipse((cx, cy - r * 0.9, cx + r, cy + r * 0.1), fill=fill)
    draw.polygon([(cx - r * 0.98, cy - r * 0.18), (cx + r * 0.98, cy - r * 0.18),
                  (cx, cy + r)], fill=fill)


# ------------------------------------------------------------------ 生日贺卡

def greeting_layer():
    """画贺卡：柔和投影 + 白卡 + 淡粉渐变 + 楷体标题。"""
    layer = Image.new('RGBA', (GREET_W, GREET_H), (0, 0, 0, 0))
    shadow = Image.new('RGBA', (GREET_W, GREET_H), (0, 0, 0, 0))
    rounded_rect(ImageDraw.Draw(shadow), (40, 30, 430, 596), 30,
                 fill=(150, 80, 105, 90))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(16)))

    draw = ImageDraw.Draw(layer)
    rounded_rect(draw, (32, 12, 438, 578), 28, fill='white')

    # 卡片里的淡粉渐变
    gw, gh = 374, 522
    grad = Image.new('RGB', (gw, gh))
    gdraw = ImageDraw.Draw(grad)
    top, bottom = hex2rgb('#fff0f5'), hex2rgb('#fffdfe')
    for yy in range(gh):
        k = yy / (gh - 1)
        gdraw.line((0, yy, gw, yy), fill=tuple(
            int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    mask = Image.new('L', (gw, gh), 0)
    rounded_rect(ImageDraw.Draw(mask), (0, 0, gw - 1, gh - 1), 20, fill=255)
    layer.paste(grad, (48, 32), mask)

    # 四角的小爱心
    for (hx, hy, hr, alpha) in ((78, 70, 7, 90), (392, 70, 7, 90),
                                (78, 520, 6, 70), (392, 520, 6, 70)):
        hl = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw_heart(ImageDraw.Draw(hl), 16, 16, hr, (255, 150, 180, alpha))
        layer.alpha_composite(hl, (hx - 16, hy - 16))

    title = load_font(('simkai.ttf', 'msyhbd.ttc'), 66)
    tw = title.getmask('生日快乐').size[0]
    draw.text(((GREET_W - tw) // 2, 92), '生日快乐', font=title, fill='#e0427a')

    draw.line((150, 202, 214, 202), fill='#f6c2d2', width=2)
    draw.line((256, 202, 320, 202), fill='#f6c2d2', width=2)
    draw_heart(draw, 235, 199, 9, '#f6a6bf')

    en = load_font(('segoesc.ttf', 'segoepr.ttf', 'msyh.ttc'), 30)
    ew = en.getmask('Happy Birthday').size[0]
    draw.text(((GREET_W - ew) // 2, 220), 'Happy Birthday', font=en, fill='#f190ad')

    body = load_font(('msyh.ttc', 'msyhbd.ttc'), 19)
    y = 306
    for line in GREET_LINES:
        lw = body.getmask(line).size[0]
        draw.text(((GREET_W - lw) // 2, y), line, font=body, fill='#6d5560')
        y += 38

    sign = load_font(('msyh.ttc',), 15)
    sw = sign.getmask(GREET_SIGN).size[0]
    draw.text(((GREET_W - sw) // 2, 452), GREET_SIGN, font=sign, fill='#b08b98')

    for hx, hr in ((205, 4), (235, 5), (265, 4)):
        draw_heart(draw, hx, 515, hr, '#f8cdda')

    # 右上角关闭按钮的白色圆底（✕ 由 Tk 按钮画）
    draw.ellipse((386, 34, 426, 74), fill='white', outline='#f4cfdb', width=2)
    return layer


def greeting_window():
    """建好贺卡窗口（不阻塞），右上角 ✕ 关掉。"""
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (sw - GREET_W) // 2, (sh - GREET_H) // 2
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.geometry(f'{GREET_W}x{GREET_H}+{x}+{y}')
    win.attributes('-topmost', 1)

    base = background_slice(x, y, GREET_W, GREET_H)
    photo = ImageTk.PhotoImage(
        Image.alpha_composite(base, greeting_layer()).convert('RGB'))
    label = tk.Label(win, image=photo, bd=0, highlightthickness=0)
    label.image = photo
    label.place(x=0, y=0, width=GREET_W, height=GREET_H)

    close = tk.Button(win, text='×', font=('微软雅黑', 14, 'bold'),
                      fg='#d98aa2', bg='white', activebackground='#ffe3ec',
                      activeforeground='#c96b85', bd=0, relief='flat',
                      highlightthickness=0, takefocus=0, cursor='hand2',
                      command=win.destroy)
    close.place(x=391, y=39, width=30, height=30)
    close.bind('<Enter>', lambda e: close.configure(bg='#ffe3ec'))
    close.bind('<Leave>', lambda e: close.configure(bg='white'))
    win.bind('<Escape>', close_all)
    return win


def show_greeting_card():
    """显示贺卡，等用户点 ✕；等待期间先把蛋糕的动画帧画好。"""
    win = greeting_window()

    def worker(i=0):
        if i >= CAKE_FRAMES or not win.winfo_exists():
            return
        prepare_cake_frame(i)
        win.after(15, worker, i + 1)

    win.after(120, worker, 0)
    root.wait_window(win)


# -------------------------------------------------------------------- 3D 蛋糕

def cake_tier(draw, cx, top_y, rx, ry, h, base, rot, n=110):
    """画一层蛋糕的圆柱面：按远近排序，一条条竖条上色，做出明暗。"""
    segs = []
    for i in range(n):
        a0 = rot + 2 * math.pi * i / n
        segs.append((math.sin(a0 + math.pi / n), a0, a0 + 2 * math.pi / n))
    segs.sort(key=lambda item: item[0])
    for sa, a0, a1 in segs:
        k = 0.74 + 0.26 * (0.5 + 0.5 * sa)
        k += 0.10 * math.exp(-((a0 - 2.3) ** 2) / 0.35)
        x0, x1 = cx + rx * math.cos(a0), cx + rx * math.cos(a1)
        y0, y1 = top_y + ry * math.sin(a0), top_y + ry * math.sin(a1)
        draw.polygon([(x0, y0), (x1, y1), (x1, y1 + h), (x0, y0 + h)],
                     fill=shade(base, k))


def cake_frosting(draw, cx, top_y, rx, ry, h, rot, phase, n=110):
    """顶边那圈奶油，带波浪下沿，会跟着蛋糕一起转。"""
    for i in range(n):
        a0 = rot + 2 * math.pi * i / n
        a1 = a0 + 2 * math.pi / n
        aa = (a0 + a1) / 2
        if math.sin(aa) < -0.15:
            continue
        drip = h * (0.34 + 0.13 * math.sin(3 * (aa - rot) + phase))
        k = 0.92 + 0.08 * (0.5 + 0.5 * math.sin(aa))
        x0, x1 = cx + rx * math.cos(a0), cx + rx * math.cos(a1)
        y0, y1 = top_y + ry * math.sin(a0), top_y + ry * math.sin(a1)
        draw.polygon([(x0, y0 - 2), (x1, y1 - 2), (x1, y1 + drip), (x0, y0 + drip)],
                     fill=shade((255, 250, 247), k))


def cake_candle(draw, glow, x, y, h, body, phase, s):
    w = 9 * s
    draw.rectangle([x - w, y - h, x + w, y], fill=body)
    for k in range(3):
        yy = y - h + (k + 0.75) * h / 3.4
        draw.rectangle([x - w, yy, x + w, yy + 4 * s], fill='#fff3f7')
    draw.ellipse([x - w, y - h - 3 * s, x + w, y - h + 3 * s],
                 fill=shade(hex2rgb(body), 1.08))
    draw.line([x, y - h, x, y - h - 6 * s], fill='#6b5a55', width=2 * s)

    fx = x + 2 * s * math.sin(phase)
    fy = y - h - 13 * s + 1.5 * s * math.cos(phase * 1.7)
    for r, alpha in ((34, 22), (22, 34), (12, 60), (6, 90)):
        glow.ellipse([fx - r * s, fy - r * s * 1.1, fx + r * s, fy + r * s * 1.1],
                     fill=(255, 214, 130, alpha))
    draw.polygon([(fx, fy - 16 * s), (fx + 7 * s, fy + 2 * s),
                  (fx, fy + 9 * s), (fx - 7 * s, fy + 2 * s)], fill='#ffb43d')
    draw.polygon([(fx, fy - 7 * s), (fx + 4 * s, fy + 3 * s),
                  (fx, fy + 7 * s), (fx - 4 * s, fy + 3 * s)], fill='#fff3b0')


def cake_star(draw, x, y, r, alpha):
    pts = []
    for i in range(8):
        ang = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.34
        pts.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
    draw.polygon(pts, fill=(255, 255, 255, alpha))


def cake_layer(rot, phase):
    """画一帧立体蛋糕（RGBA，2 倍尺寸抗锯齿）。"""
    s = CAKE_S
    w, h = CAKE_W * s, CAKE_H * s
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx = w // 2
    pcy = 470 * s

    # 盘子投影
    for k, alpha in ((1.00, 18), (1.06, 12), (1.12, 8)):
        gdraw.ellipse([cx - 225 * s * k, pcy - 22 * s, cx + 225 * s * k, pcy + 30 * s],
                      fill=(190, 120, 150, alpha))
    draw.ellipse([cx - 225 * s, pcy - 26 * s, cx + 225 * s, pcy + 26 * s],
                 fill='#f7edf2')
    draw.ellipse([cx - 225 * s, pcy - 26 * s, cx + 225 * s, pcy + 26 * s],
                 outline='#ead7df', width=s)
    draw.ellipse([cx - 190 * s, pcy - 20 * s, cx + 190 * s, pcy + 6 * s],
                 fill='#fdf7fa')

    tiers = [
        (340 * s, 185 * s, 48 * s, 90 * s, '#ffc2d6', 0.0),
        (265 * s, 140 * s, 38 * s, 75 * s, '#ffe3c2', 0.7),
        (200 * s, 95 * s, 28 * s, 65 * s, '#ffd0e2', 1.4),
    ]
    for idx, (ty, rx, ry, th, color, ph) in enumerate(tiers):
        cake_tier(draw, cx, ty, rx, ry, th, hex2rgb(color), rot)
        rnd = random.Random(idx * 7 + 1)      # 糖针固定位置，跟着蛋糕转
        for _ in range(26):
            a = rot + rnd.uniform(0, 2 * math.pi)
            yy = rnd.uniform(0.42, 0.95) * th
            if math.sin(a) < 0:
                continue
            x = cx + rx * math.cos(a) * 0.99
            y = ty + ry * math.sin(a) + yy
            draw.ellipse([x - 2 * s, y - 2 * s, x + 2 * s, y + 2 * s],
                         fill=rnd.choice(['#fff6fa', '#ffd166', '#8ecae6', '#b7e4c7']))
        cake_frosting(draw, cx, ty, rx, ry, th, rot, ph)
        draw.ellipse([cx - rx, ty - ry, cx + rx, ty + ry],
                     fill='#fffaf7', outline='#f0dfe6')

    # 蜡烛按前后顺序画
    ty, rx, ry, th, _, _ = tiers[2]
    candles = []
    for i in range(3):
        a = rot + i * 2 * math.pi / 3 + 0.4
        candles.append((math.sin(a), cx + rx * 0.52 * math.cos(a),
                        ty + ry * 0.52 * math.sin(a)))
    for sa, x, y in sorted(candles):
        cake_candle(draw, gdraw, x, y, 34 * s,
                    '#ff8fb3' if sa > 0 else '#f7b8ce', phase, s)

    rnd = random.Random(9)
    for k in range(12):
        x = cx + rnd.uniform(-240, 240) * s
        y = rnd.uniform(120, 470) * s
        r = (2.5 + 3.5 * abs(math.sin(phase * 1.3 + k))) * s
        cake_star(gdraw, x, y, r, 160)

    img = Image.alpha_composite(img, glow).resize((CAKE_W, CAKE_H), Image.LANCZOS)

    wish = load_font(('simkai.ttf', 'msyh.ttc'), 30)
    wdraw = ImageDraw.Draw(img)
    tw = wish.getmask('许个愿吧').size[0]
    wdraw.text(((CAKE_W - tw) // 2, 530), '许个愿吧', font=wish, fill='#e489a6')
    return img


def prepare_cake_frame(i):
    """合成第 i 帧：背景切片 + 蛋糕，缓存成 PhotoImage。"""
    if i in cake_cache:
        return cake_cache[i]
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (sw - CAKE_W) // 2, (sh - CAKE_H) // 2
    base = background_slice(x, y, CAKE_W, CAKE_H)
    layer = cake_layer(2 * math.pi * i / CAKE_FRAMES, i * 0.9)
    photo = ImageTk.PhotoImage(Image.alpha_composite(base, layer).convert('RGB'))
    cake_cache[i] = photo
    return photo


def show_cake(seconds=CAKE_SECONDS):
    """贺卡关掉之后，在背景上展示缓缓旋转的 3D 蛋糕。"""
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (sw - CAKE_W) // 2, (sh - CAKE_H) // 2
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.geometry(f'{CAKE_W}x{CAKE_H}+{x}+{y}')
    win.attributes('-topmost', 1)
    label = tk.Label(win, bd=0, highlightthickness=0)
    label.place(x=0, y=0)
    win.bind('<Escape>', close_all)

    for i in range(CAKE_FRAMES):          # 贺卡开得不够久的话，这里补画
        prepare_cake_frame(i)
    frames = [cake_cache[i] for i in range(CAKE_FRAMES)]
    label.configure(image=frames[0])

    start = time.time()
    i = 0
    while time.time() - start < seconds:
        if not win.winfo_exists():
            return
        label.configure(image=frames[i % CAKE_FRAMES])
        try:
            root.update()
        except tk.TclError:
            return
        time.sleep(0.1)
        i += 1

    for step in range(10, -1, -1):        # 慢慢淡出
        if not win.winfo_exists():
            return
        try:
            win.attributes('-alpha', step / 10.0)
            root.update()
        except tk.TclError:
            return
        time.sleep(0.04)
    try:
        win.destroy()
    except tk.TclError:
        pass


def idle_wait(seconds):
    """等待若干秒，期间继续处理界面事件，让 Esc 随时都能退出。"""
    end = time.time() + seconds
    while time.time() < end:
        try:
            root.update()
        except tk.TclError:
            return
        time.sleep(0.02)


def main():
    global root, USE_CARDS
    root = tk.Tk()
    root.title('生日快乐')
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    # 去掉标题栏，铺满整块屏幕，把图片当背景
    root.overrideredirect(True)
    root.geometry(f'{sw}x{sh}+0+0')
    root.attributes('-topmost', 1)
    show_background(sw, sh)
    USE_CARDS = Image is not None and cards_supported()
    root.bind_all('<Escape>', close_all)
    root.update()
    root.focus_force()
    idle_wait(2)                # 先单独展示 2 秒背景图
    points = heart_points(100, sw, sh)
    # 拼成爱心
    for (x, y) in points:
        win = create_popup(x, y)
        hearts.append(win)
        root.update()
        time.sleep(0.03)
    idle_wait(1)
    # 爱心消失
    for w in hearts:
        try:
            if w.winfo_exists():
                w.destroy()
        except tk.TclError:
            pass
    # 漫天祝福语弹窗
    count = (sw // CARD_W) * (sh // 40) + 50
    for _ in range(count):
        x = random.randint(0, sw - CARD_W)
        y = random.randint(0, sh - CARD_H)
        win = create_popup(x, y)
        all_wins.append(win)
        root.update()
        time.sleep(0.005)
    idle_wait(10)
    # 窗口慢慢关闭
    interval = 1.0 / len(all_wins) if all_wins else 0
    for win in all_wins:
        try:
            if win.winfo_exists():
                win.destroy()
        except tk.TclError:
            pass
        root.update()
        time.sleep(interval)
    idle_wait(1.5)              # 弹窗关完后，留一点时间只看背景图
    show_greeting_card()        # 贺卡：点右上角 ✕ 关掉
    show_cake()                 # 贺卡关掉后，立体蛋糕登场
    idle_wait(1.5)              # 蛋糕淡出后停留一下
    try:
        root.destroy()
    except tk.TclError:
        pass


if __name__ == "__main__":
    main()
