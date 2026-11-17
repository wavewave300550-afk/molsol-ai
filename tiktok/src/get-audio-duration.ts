import { ALL_FORMATS, Input, UrlSource } from "mediabunny";

/** Duration of an audio file in seconds (Mediabunny, as the Remotion skill recommends). */
export const getAudioDuration = async (src: string): Promise<number> => {
  const input = new Input({ formats: ALL_FORMATS, source: new UrlSource(src) });
  try {
    return await input.computeDuration();
  } finally {
    input.dispose();
  }
};
