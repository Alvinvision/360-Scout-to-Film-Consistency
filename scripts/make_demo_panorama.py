"""Generate a labeled, original 2:1 panorama without external media."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw
dest = Path(sys.argv[1] if len(sys.argv) > 1 else 'demo_panorama.png')
dest.parent.mkdir(parents=True, exist_ok=True)
im = Image.new('RGB', (2048, 1024), '#81b6d2')
draw = ImageDraw.Draw(im)
draw.rectangle((0,512,2047,1023), fill='#627655')
colors = ['#af5447','#cda65a','#557da8','#9580b1','#6b9d83','#ad7d54','#637d97','#a75778']
for i, color in enumerate(colors):
    x = i*256
    draw.rectangle((x+20,350,x+236,680), fill=color, outline='white', width=3)
    draw.text((x+40,390), f'SECTOR {i+1} / YAW {i*45}', fill='white', font_size=18)
    draw.rectangle((x+75,510,x+175,680), fill='#25313b')
for y in (256,512,768): draw.line((0,y,2048,y), fill='#d9e3e7', width=2)
im.save(dest)
print(dest.resolve())
