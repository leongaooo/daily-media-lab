import React from 'react';
import {Composition} from 'remotion';
import data from './data.json';
import {EditorialVideo} from './Composition';

export const Root: React.FC = () => (
  <Composition id="Editorial" component={EditorialVideo} defaultProps={data}
    durationInFrames={data.scenes.reduce((sum, scene) => sum + scene.duration, 0)}
    fps={data.fps} width={data.width} height={data.height} />
);
