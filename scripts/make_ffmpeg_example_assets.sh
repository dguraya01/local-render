#!/bin/sh
# Regenerates examples/ffmpeg/assets: three 1920x1080 slides (drawn with headless Chrome)
# and a short synthesized music bed (ffmpeg). Only needed if you change the slides.
set -e
cd "$(dirname "$0")/.."
OUT=examples/ffmpeg/assets
CHROME="${LR_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"

slide() { # n, title, line, accent
  cat > "$TMP/s$1.html" <<EOF
<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0b0d17;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
.bg{position:absolute;inset:0;background:radial-gradient(circle at 78% 22%,#1d2448 0,#0b0d17 58%)}
.orb{position:absolute;right:-180px;top:-180px;width:820px;height:820px;border-radius:50%;border:3px solid $4;opacity:.35}
.orb2{position:absolute;right:40px;top:40px;width:380px;height:380px;border-radius:50%;background:$4;opacity:.12}
.n{position:absolute;left:180px;top:250px;font-size:150px;font-weight:900;color:$4;letter-spacing:-4px}
.t{position:absolute;left:170px;top:420px;font-size:250px;font-weight:900;color:#f4f1ea;letter-spacing:-10px}
.l{position:absolute;left:182px;top:745px;font-size:52px;color:#9aa1c0}
.bar{position:absolute;left:182px;top:840px;width:240px;height:12px;background:$4;border-radius:6px}
.f{position:absolute;right:120px;bottom:90px;font-size:30px;color:#4d5476;letter-spacing:6px;font-weight:700}
</style></head><body><div class="bg"></div><div class="orb"></div><div class="orb2"></div>
<div class="n">0$1</div><div class="t">$2</div><div class="l">$3</div><div class="bar"></div>
<div class="f">LOCAL-RENDER</div></body></html>
EOF
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1920,1080 --screenshot="$OUT/slide$1.png" "file://$TMP/s$1.html" >/dev/null 2>&1
}

slide 1 "Write." "Claude writes the animation code in chat." "#ff5c39"
slide 2 "Pack." "You get one zip: a render pack." "#9fb6ff"
slide 3 "Render." "Your own computer renders it in about a minute." "#c6ff3d"

# soft A-major pad with a slow swell, light echo, stereo, 10 s
ffmpeg -v error -y -f lavfi -i "aevalsrc='(0.11*sin(2*PI*110*t)+0.07*sin(2*PI*164.81*t)+0.06*sin(2*PI*220*t)+0.045*sin(2*PI*277.18*t)+0.035*sin(2*PI*329.63*t))*(0.75+0.25*sin(2*PI*0.2*t))':s=44100:d=10" \
  -af "lowpass=f=1600,aecho=0.8:0.6:180|360:0.25|0.12,pan=stereo|c0=c0|c1=c0,afade=t=in:d=1" \
  -c:a aac -b:a 128k "$OUT/music.m4a"
ls -la "$OUT"
