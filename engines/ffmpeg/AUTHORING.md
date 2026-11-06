# ffmpeg: authoring guide

Best for slideshows, photo montages, image sequences, and stills + music. No code runs:
the pack is data (a JSON description plus assets), so it is the lowest-risk engine.

## Files

```
render.json          entry: "src/slideshow.json", audio: "assets/music.m4a" (optional)
src/slideshow.json   what to show
assets/              the images and audio
```

## Slideshow

```json
{
  "slides": [
    { "image": "assets/01.jpg", "duration": 3.5 },
    { "image": "assets/02.jpg", "duration": 3.5 }
  ],
  "transition": { "type": "fade", "duration": 0.8 },
  "ken_burns": { "zoom": 1.08 }
}
```

- Video length = sum of slide durations − (slides − 1) × transition duration. Put that
  number in render.json `duration`.
- `transition.type` is any ffmpeg `xfade` transition: `fade`, `fadeblack`, `wipeleft`,
  `slideleft`, `smoothleft`, `circleopen`, `dissolve`, `pixelize`, `radial`, ...
- Images are scaled to cover the frame and center-cropped. Slides alternate zooming in and out;
  set `"ken_burns": false` for static slides.
- Text on slides: draw it into the images (the sandbox can render slides with HTML/PIL);
  ffmpeg builds without `drawtext` are common, so it isn't used.

## Image sequence

```json
{ "sequence": { "pattern": "assets/frames/frame_%04d.png", "start_number": 1 } }
```

Frames play at render.json `fps`; `duration` trims the end.

## Still + audio

A single slide whose duration equals the audio length, with `"ken_burns": false`.

## Preview inside the sandbox

ffmpeg is usually available in sandboxes, so `build_pack.py preview <dir> --time 2` normally
works and is cheap.
