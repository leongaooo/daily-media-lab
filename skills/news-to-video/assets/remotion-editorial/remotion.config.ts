import {Config} from '@remotion/cli/config';
Config.setOverwriteOutput(true);
Config.setVideoImageFormat('jpeg');
// Allow an existing local browser instead of requiring a separate download.
if (process.env.NEWS_TO_VIDEO_BROWSER) {
  Config.setBrowserExecutable(process.env.NEWS_TO_VIDEO_BROWSER);
}
