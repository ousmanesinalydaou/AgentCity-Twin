import fr from "./fr.json";
import bm from "./bm.json";

export type Language = "en" | "fr" | "bm";
export type Translate = (text: string) => string;
export const languages = { en: "English", fr: "Français", bm: "Bamanankan" };
const dictionaries: Record<Language, Record<string, string>> = {
  en: {"agent.completed":"Agent completed","agent.failed":"Agent model failed"}, fr, bm,
};
export function translate(language: Language): Translate {
  const dictionary = dictionaries[language];
  return (text) => dictionary[text] ?? text;
}
export const locales: Record<Language, string> = { en: "en-GB", fr: "fr-FR", bm: "bm-ML" };

