export interface CharacterEvent {
  start: number;
  end: number;
  pose: string;
  emotion: string;
  head: string;
}

export interface MouthCue {
  start: number;
  end: number;
  shape: string;
}

export interface BlinkCue {
  start: number;
  end: number;
}

export interface CharacterTrack {
  version: number;
  character_id: string;
  duration_seconds: number;
  base_pose: string;
  base_emotion: string;
  events: CharacterEvent[];
  mouth_cues: MouthCue[];
  blink_cues: BlinkCue[];
}

export interface CharacterAsset {
  path: string;
}

export interface CharacterManifest {
  version: number;
  character_id: string;
  assets: Record<string, Record<string, CharacterAsset>>;
  fallbacks: Record<string, string>;
  metadata?: Record<string, unknown>;
}

export interface CharacterState {
  pose: string;
  emotion: string;
  head: string;
  mouth: string;
  blinking: boolean;
}

const activeAt = <T extends {start: number; end: number}>(items: T[], time: number): T | undefined =>
  items.find((item) => time >= item.start && time < item.end);

export const resolveCharacterState = (track: CharacterTrack, time: number): CharacterState => {
  const event = activeAt(track.events, time);
  const emotion = event?.emotion ?? track.base_emotion;
  const mouthCue = activeAt(track.mouth_cues, time);
  return {
    pose: event?.pose ?? track.base_pose,
    emotion,
    head: event?.head ?? "M",
    mouth: mouthCue?.shape ?? (emotion.startsWith("worried") || emotion.startsWith("sad") ? "m_b_close_s" : "m_b_close_h"),
    blinking: Boolean(activeAt(track.blink_cues, time)),
  };
};
