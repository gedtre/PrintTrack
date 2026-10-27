from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).parent / 'printtrack' / 'assets'
root.mkdir(exist_ok=True)
im = Image.new('RGBA', (256, 256), '#101d33')
d = ImageDraw.Draw(im)
d.rounded_rectangle((24, 24, 232, 232), radius=48, fill='#0d9473')
d.rounded_rectangle((60, 94, 196, 182), radius=18, fill='white')
d.rectangle((82, 57, 174, 114), fill='#e6fff7')
d.rounded_rectangle((83, 146, 173, 205), radius=6, fill='#101d33')
d.line((99, 166, 157, 166), fill='#10b981', width=7)
d.line((99, 184, 143, 184), fill='#10b981', width=7)
d.ellipse((168, 113, 181, 126), fill='#10b981')
im.save(root / 'icon.png')
im.save(root / 'icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
