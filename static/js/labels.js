export const VOICE_LABELS = {
  'pt-BR-AntonioNeural': 'Antônio Neural',
  'pt-BR-FranciscaNeural': 'Francisca Neural',
  'pt-PT-DuarteNeural': 'Duarte Neural',
  'pt-PT-RaquelNeural': 'Raquel Neural',
  'en-US-GuyNeural': 'Guy Neural',
  'en-US-JennyNeural': 'Jenny Neural',
  'es-ES-AlvaroNeural': 'Álvaro Neural',
  'fr-FR-HenriNeural': 'Henri Neural',
  'de-DE-ConradNeural': 'Conrad Neural',
  'it-IT-DiegoNeural': 'Diego Neural',
  'ru-RU-DmitryNeural': 'Dmitry Neural'
};

export const LOCALE_NAMES = {
  'pt-BR': 'Português - BR',
  'pt-PT': 'Português - PT',
  'en-US': 'Inglês - EUA',
  'es-ES': 'Espanhol - ES',
  'fr-FR': 'Francês - FR',
  'de-DE': 'Alemão - DE',
  'it-IT': 'Italiano - IT',
  'ru-RU': 'Russo - RU'
};

export const LANG_CODE_NAMES = {
  'pt': 'Português',
  'en': 'Inglês',
  'es': 'Espanhol',
  'fr': 'Francês',
  'de': 'Alemão',
  'it': 'Italiano',
  'ru': 'Russo'
};

export function getLocaleFromVoice(voiceShortname) {
  if (!voiceShortname) return null;
  const parts = voiceShortname.split('-');
  if (parts.length >= 3) return `${parts[0]}-${parts[1]}`;
  return null;
}

export function formatVoiceLabel(voiceShortname) {
  if (!voiceShortname) return '--';
  if (VOICE_LABELS[voiceShortname]) return VOICE_LABELS[voiceShortname];
  const parts = voiceShortname.split('-');
  const raw = parts.slice(2).join('-');
  return raw.replace(/Neural$/, ' Neural');
}

export function formatLanguageLabel(voiceShortname, detectedLangCode) {
  const locale = getLocaleFromVoice(voiceShortname);
  if (locale && LOCALE_NAMES[locale]) return LOCALE_NAMES[locale];
  if (detectedLangCode && LANG_CODE_NAMES[detectedLangCode]) {
    return LANG_CODE_NAMES[detectedLangCode];
  }
  return detectedLangCode || '--';
}
