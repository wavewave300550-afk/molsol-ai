/**
 * Render settings for every TikTok episode: 1080x1920, 30 fps (set on the
 * composition), H.264 + AAC in an MP4 that plays on iPhone.
 *
 * These apply to the `remotion` CLI (studio, render). The scripts in
 * scripts/ call the CLI, so they pick these up too.
 * All options: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setOverwriteOutput(true);
Config.setDefaultPremountInSeconds(2);

Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setCrf(18);
Config.setX264Preset("medium");
Config.setAudioCodec("aac");
Config.setAudioBitrate("192k");
