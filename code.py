#!/usr/bin/env python3
"""يولّد أيقونة مساح وشاشة البداية وصور المتجر. يعمل داخل GitHub Actions بعد `cap add android`."""
import glob, os, re, sys
from PIL import Image, ImageDraw, ImageFont, features

G9 = (20, 41, 26)
G7 = (43, 86, 56)
ORANGE = (255, 106, 26)
WHITE = (255, 255, 255)
SS = 4  # تنعيم الحواف

RES = 'android/app/src/main/res'
OUT = 'store-assets'


def contours(size, alpha=22):
    """خطوط كنتورية خفيفة للخلفية"""
    n = size * SS
    layer = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = n * 0.105
    for cx, cy, maxr in ((n * 0.10, n * 1.18, n * 1.5), (n * 0.98, n * -0.22, n * 1.1)):
        r = step
        while r < maxr:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, alpha), width=max(1, n // 300))
            r += step
    return layer.resize((size, size), Image.LANCZOS)


def mark(size):
    """شعار: قطعة أرض برتقالية بأربع زوايا بيضاء. الإحداثيات على شبكة 108 (المنطقة الآمنة 21-87)"""
    n = size * SS
    k = n / 108.0
    layer = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [(29, 41), (60, 27), (82, 50), (72, 81), (37, 77)]
    P = [(x * k, y * k) for x, y in pts]
    d.polygon(P, fill=ORANGE)
    d.line(P + [P[0]], fill=WHITE, width=int(3.4 * k), joint='curve')
    r = 5.6 * k
    for x, y in P:
        d.ellipse((x - r, y - r, x + r, y + r), fill=WHITE, outline=G9, width=int(2.2 * k))
    return layer.resize((size, size), Image.LANCZOS)


def base(size, kind):
    """kind: square (أيقونة قديمة بزوايا مدوّرة) | round | full"""
    img = Image.new('RGBA', (size, size), G9 + (255,))
    img.alpha_composite(contours(size))
    img.alpha_composite(mark(size))
    if kind == 'full':
        return img
    mask = Image.new('L', (size * SS, size * SS), 0)
    md = ImageDraw.Draw(mask)
    if kind == 'round':
        md.ellipse((0, 0, size * SS - 1, size * SS - 1), fill=255)
    else:
        md.rounded_rectangle((0, 0, size * SS - 1, size * SS - 1), radius=int(size * SS * 0.22), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def android_icons():
    legacy = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
    fg = {'mdpi': 108, 'hdpi': 162, 'xhdpi': 216, 'xxhdpi': 324, 'xxxhdpi': 432}
    for dens in legacy:
        d = f'{RES}/mipmap-{dens}'
        save(base(legacy[dens], 'square'), f'{d}/ic_launcher.png')
        save(base(legacy[dens], 'round'), f'{d}/ic_launcher_round.png')
        save(mark(fg[dens]), f'{d}/ic_launcher_foreground.png')
    os.makedirs(f'{RES}/mipmap-anydpi-v26', exist_ok=True)
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
           '    <background android:drawable="@color/ic_launcher_background"/>\n'
           '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
           '</adaptive-icon>\n')
    for name in ('ic_launcher.xml', 'ic_launcher_round.xml'):
        open(f'{RES}/mipmap-anydpi-v26/{name}', 'w').write(xml)
    os.makedirs(f'{RES}/values', exist_ok=True)
    open(f'{RES}/values/ic_launcher_background.xml', 'w').write(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <color name="ic_launcher_background">#14291A</color>\n</resources>\n')


def splash():
    for p in glob.glob(f'{RES}/drawable*/splash.png'):
        w, h = Image.open(p).size
        img = Image.new('RGBA', (w, h), G9 + (255,))
        s = max(w, h)
        c = contours(s)
        img.alpha_composite(c.crop((0, 0, w, h)))
        m = int(min(w, h) * 0.34)
        img.alpha_composite(mark(m), ((w - m) // 2, (h - m) // 2))
        img.convert('RGB').save(p)


def patch_styles():
    """لون شريط الحالة والتنقل وخلفية شاشة البداية. يتخطى بصمت إن لم يجد القالب المتوقع"""
    p = f'{RES}/values/styles.xml'
    if not os.path.exists(p):
        return
    s = open(p, encoding='utf-8').read()
    if 'masah-patched' in s:
        return
    add = ('\n        <item name="android:statusBarColor">#14291A</item>'
           '\n        <item name="android:navigationBarColor">#14291A</item>'
           '\n        <item name="android:windowLightStatusBar">false</item>')
    s2 = re.sub(r'(<style name="AppTheme\.NoActionBar"[^>]*>)', r'\1' + add, s, count=1)
    s2 = re.sub(r'(<style name="AppTheme\.NoActionBarLaunch" parent="Theme\.SplashScreen"[^>]*>)',
                r'\1\n        <item name="windowSplashScreenBackground">#14291A</item>', s2, count=1)
    s2 = s2.replace('<resources>', '<resources>\n    <!-- masah-patched -->', 1)
    open(p, 'w', encoding='utf-8').write(s2)


def find_font():
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf'):
        if os.path.exists(f):
            return f
    return None


def store_assets():
    save(base(512, 'full').convert('RGB'), f'{OUT}/icon-512-square.png')
    save(base(512, 'square'), f'{OUT}/icon-512-rounded.png')
    W, H = 1024, 500
    img = Image.new('RGBA', (W, H), G9 + (255,))
    img.alpha_composite(contours(max(W, H)).crop((0, 0, W, H)))
    m = 330
    img.alpha_composite(mark(m), (W - m - 90, (H - m) // 2))
    font = find_font()
    if font and features.check('raqm'):
        d = ImageDraw.Draw(img)
        big = ImageFont.truetype(font, 150)
        small = ImageFont.truetype(font, 44)
        d.text((90, 150), 'مساح', font=big, fill=WHITE, direction='rtl', language='ar')
        d.text((90, 330), 'قِس أرضك بالـGPS', font=small, fill=(227, 236, 224), direction='rtl', language='ar')
        d.text((90, 392), 'دونم · هكتار · بدون إنترنت', font=small, fill=ORANGE, direction='rtl', language='ar')
    save(img.convert('RGB'), f'{OUT}/feature-1024x500.png')


if __name__ == '__main__':
    if os.path.isdir(RES):
        android_icons()
        splash()
        patch_styles()
        print('android assets ok')
    store_assets()
    print('store assets ok')
