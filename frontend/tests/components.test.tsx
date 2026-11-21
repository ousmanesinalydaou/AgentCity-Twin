import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AskPanel, Timeline } from "@/components/overview";
import { translate } from "@/i18n";

afterEach(cleanup);
const t=translate("en");

describe("simulation controls", () => {
  it("uses a suggested scenario without submitting it", () => {
    const choose=vi.fn();
    const submit=vi.fn();
    const preset={id:"university-accident",label:"University corridor accident",city_id:"debrecen",kind:"Emergency",
      location:"University of Debrecen",coordinates:[21.6257,47.5533] as [number,number],time:"17:00",duration:60,
      severity:4,population:1200,prompt:"An accident happens near the University of Debrecen.",brief:"Compare responses."};
    render(<AskPanel value="" change={vi.fn()} submit={submit} busy={false} t={t} demos={[preset]} selected={null} choose={choose}/>);
    fireEvent.click(screen.getByRole("button",{name:"University corridor accident"}));
    expect(choose).toHaveBeenCalledWith(preset);
    expect(submit).not.toHaveBeenCalled();
  });
  it("exposes translated states and prevents playback before a run", () => {
    render(<Timeline tick={0} change={vi.fn()} mode="Current" modeChange={vi.fn()} t={translate("fr")}
      run={null} playing={false} togglePlay={vi.fn()}/>);
    expect(screen.getByRole("button",{name:"Actuel"}).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button",{name:"+15 min"}).hasAttribute("disabled")).toBe(true);
  });
});

