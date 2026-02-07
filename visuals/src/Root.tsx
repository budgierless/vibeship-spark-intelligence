import React from "react";
import { Composition } from "remotion";
import { IntelligenceFunnel } from "./IntelligenceFunnel";
import { SPARK_THEME as T } from "./theme";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Still: Funnel scene (frame 90 = everything visible) */}
      <Composition
        id="FunnelStill"
        component={IntelligenceFunnel}
        durationInFrames={420}
        fps={30}
        width={T.width}
        height={T.height}
      />

      {/* Full 14-second video (4 scenes) */}
      <Composition
        id="IntelligenceFunnel"
        component={IntelligenceFunnel}
        durationInFrames={420}
        fps={30}
        width={T.width}
        height={T.height}
      />
    </>
  );
};
