# remotion: authoring guide

Best for React-based motion graphics: springs, sequences, data-driven video, captions.
The Remotion CLI renders the composition; on Apple Silicon it uses VideoToolbox.

## Files

The Remotion project lives in `src/`:

```
render.json            entry: "src/index.ts", dependencies.npm_dir: "src",
                       engine_options.composition: "Main"
src/package.json       exact versions: remotion, @remotion/cli, react, react-dom
src/tsconfig.json      optional
src/index.ts           registerRoot(Root)
src/Root.tsx           <Composition id="Main" ... calculateMetadata=...>
src/Main.tsx           the video
assets/                images/fonts/audio; for Remotion, put files that the video
                       loads with staticFile() in src/public/ instead
```

`src/package.json` (pin exact versions; all four must share one Remotion version):

```json
{ "private": true, "dependencies": {
  "remotion": "4.0.541", "@remotion/cli": "4.0.541", "react": "19.2.0", "react-dom": "19.2.0" } }
```

## Keep render.json the source of truth

local-render passes `props.lr = {width, height, fps, durationInFrames}` from render.json.
Adopt it with `calculateMetadata`:

```tsx
export const Root: React.FC = () => (
  <Composition id="Main" component={Main} width={1920} height={1080} fps={30} durationInFrames={150}
    defaultProps={{ title: "Hello" }}
    calculateMetadata={({ props }) => (props.lr ? { ...props.lr } : {})} />
);
```

Custom props go in `engine_options.props`; they are merged with `lr`.

## Rules

- Animate only with `useCurrentFrame()`, `interpolate()`, `spring()`, `<Sequence>`.
  No CSS transitions, `setTimeout` or `Date.now()`.
- Fonts: load local files with `@remotion/fonts` or a CSS `@font-face` pointing at
  `staticFile(...)`; do not rely on Google Fonts at render time.
- Don't commit `node_modules`. First render runs `npm install` in `src/` and Remotion
  downloads its headless browser once.

## engine_options

| key | default | meaning |
|---|---|---|
| `composition` | `"Main"` | composition id to render |
| `props` | `{}` | input props for the composition |

## Preview inside the sandbox

`build_pack.py preview` runs `npx remotion still` and needs npm network access plus a
browser download. In a sandbox without them, skip the preview.
