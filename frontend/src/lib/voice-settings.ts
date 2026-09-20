export type VoiceId = "cove" | "juniper" | "maple" | "spruce" | "ember" | "vale" | "breeze" | "arbor" | "sol";
export type AgentPresetId = "rosario" | "clara" | "serena";
export type OpeningLanguage = "en" | "es";

export interface VoiceSettings {
  voice: VoiceId;
  preset: AgentPresetId;
  opening_language: OpeningLanguage;
  guidance: string;
}

export interface AgentPreset {
  id: AgentPresetId;
  name: string;
  description: string;
  voice: VoiceId;
}

export interface VoiceOption {
  id: VoiceId;
  name: string;
  description: string;
}

export interface VoiceSettingsDocument {
  settings: VoiceSettings;
  presets: AgentPreset[];
  voices: VoiceOption[];
}

export function sameVoiceSettings(a: VoiceSettings, b: VoiceSettings): boolean {
  return a.voice === b.voice && a.preset === b.preset && a.opening_language === b.opening_language && a.guidance === b.guidance;
}
