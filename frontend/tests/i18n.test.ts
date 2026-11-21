import { describe, expect, it } from "vitest";
import { languages, translate } from "@/i18n";

describe("workspace locales", ()=>{
  it("offers the three required languages and an English fallback", ()=>{
    expect(Object.keys(languages)).toEqual(["en","fr","bm"]);
    expect(translate("fr")("Scenarios")).toBe("Scénarios");
    expect(translate("bm")("Scenarios")).toBe("Kɛwalew");
    expect(translate("fr")("External incident name")).toBe("External incident name");
  });
});

