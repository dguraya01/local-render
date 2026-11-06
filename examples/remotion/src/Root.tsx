import React from "react";
import { Composition } from "remotion";
import { Main, MainProps } from "./Main";

// local-render passes render.json's size/fps/length as props.lr, so render.json stays the
// single source of truth. The literal values below are only used in Remotion Studio.
type Props = MainProps & { lr?: { width: number; height: number; fps: number; durationInFrames: number } };

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={Main as React.FC<Props>}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={150}
    defaultProps={{ cloudMinutes: 45, localSeconds: 60 } as Props}
    calculateMetadata={({ props }) => (props.lr ? { ...props.lr } : {})}
  />
);
