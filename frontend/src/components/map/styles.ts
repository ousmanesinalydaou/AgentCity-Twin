import type { ExpressionSpecification, LayerSpecification, StyleSpecification } from "maplibre-gl";

export const mapStyles: Record<string, string> = {
  fiord: "https://tiles.openfreemap.org/styles/fiord",
  dark: "https://tiles.openfreemap.org/styles/dark",
  liberty: "https://tiles.openfreemap.org/styles/liberty",
};

const strokes: Record<string, [string, number]> = {
  service: ["#203247", .585], minor: ["#2c3e53", .9], tertiary: ["#3c5064", 1.35],
  secondary: ["#465c72", 1.75], primary: ["#526a7e", 2.2], trunk: ["#526a7e", 2.7],
  motorway: ["#526a7e", 2.7], rail: ["#253447", 1],
};

function fill(sourceLayer: string, color: string, sideFilter?: ExpressionSpecification): LayerSpecification {
  return { id: "base-" + sourceLayer, type: "fill", source: "snapshot",
    filter: sideFilter ? ["all", ["==", ["get", "layer"], sourceLayer], sideFilter] : ["==", ["get", "layer"], sourceLayer],
    paint: { "fill-color": color, "fill-opacity": .76 } };
}
export const localStyle: StyleSpecification = {
  version: 8,
  glyphs: "/maps/fonts/{fontstack}/{range}.pbf",
  sources: {
    snapshot: {type:"geojson",data:"/maps/debrecen.geojson", attribution:"© <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap contributors</a> · <a href='https://openfreemap.org/'>OpenFreeMap</a>"},
  },
  layers: [
    {id:"base-background",type:"background",paint:{"background-color":"#101b2a"}},
    fill("landuse", "#182637"),
    fill("landcover", "#18342e", ["in", ["get", "class"], ["literal", ["grass", "wood"]]]),
    fill("park", "#17382c"),
    fill("water", "#163649"),
    ...Object.entries(strokes).map(([category, [color, width]]) => ({
      id: "base-" + category, type: "line", source: "snapshot",
      filter: ["all", ["==", ["get", "layer"], "transportation"], ["==", ["get", "class"], category]],
      layout: {"line-cap":"round", "line-join":"round"},
      paint: {"line-color":color, "line-width":["interpolate",["linear"],["zoom"],10,width * .42,13,width,16,width * 2.7]},
    } as LayerSpecification)),
  ],
};

