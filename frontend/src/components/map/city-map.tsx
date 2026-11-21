"use client";

import maplibregl, { type GeoJSONSource, type Map as MapInstance } from "maplibre-gl";
import { Crosshair, Layers3, Maximize, Minus, MoveDownRight, Plus, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { City, Coordinates, Frame, Incident, Layers } from "@/lib/types";
import type { Translate } from "@/i18n";
import { localStyle, mapStyles } from "./styles";

export const defaultLayers = ["Traffic", "Transit", "Air quality", "Incidents", "Sensors", "Environmental zones", "Predicted congestion", "Intervention paths", "Risk zones", "Recommendations", "City boundary"];
const colors: Record<string, string> = {
  Traffic:"#36d6a8", Transit:"#ae8bfa", Incidents:"#fd7d70", "Air quality":"#70dbaa",
  "Environmental zones":"#368f78", Sensors:"#66aaff", "Campus activity":"#9b91ff",
  Energy:"#e9bb66", Construction:"#e5a35e", Recommendations:"#4be1b3",
  "Predicted congestion":"#b49afa", "Intervention paths":"#45eacc", "Risk zones":"#e89070", "City boundary":"#9db7cc",
  "Sensor coverage":"#689beb",
};
const EMPTY: GeoJSON.FeatureCollection = {type:"FeatureCollection",features:[]};
const campusLabel = { title:"University of Debrecen", subtitle:"Campus district" };

type Props = {
  city:City; data:Layers|null; incidents:Incident[]; selected:Coordinates|null; select:(value:Coordinates)=>void;
  frame?:Frame; mode:string; radius?:number; forecastOrigin?:Coordinates; duration?:number; style?:string; t:Translate; expanded?:boolean; startPicking?:boolean;
};

function pulseRegion(coords:Coordinates, radius:number): GeoJSON.Polygon {
  const ring: Coordinates[] = [];
  for (let index=0;index<=48;index++) {
    const angle = index * Math.PI / 24;
    ring.push([
      coords[0] + Math.cos(angle) * radius / (111195*Math.cos(coords[1]*Math.PI/180)),
      coords[1] + Math.sin(angle) * radius / 111195,
    ]);
  }
  return {type:"Polygon",coordinates:[ring]};
}

function intersectsZone(points:number[][], center:Coordinates, radius:number) {
  const scale=Math.cos(center[1]*Math.PI/180);
  const offsets=points.map(([lng,lat])=>[(lng-center[0])*scale,lat-center[1]]);
  const threshold=(radius/111195)**2;
  return offsets.some(([x,y],index)=>{
    if(x*x+y*y<=threshold)return true;
    if(!index)return false;
    const [a,b]=offsets[index-1], dx=x-a, dy=y-b;
    const length=dx*dx+dy*dy;
    if(!length)return false;
    const fraction=Math.max(0,Math.min(1,-(a*dx+b*dy)/length));
    return (a+fraction*dx)**2+(b+fraction*dy)**2<=threshold;
  });
}

function overlayData(data:Layers|null, frame:Frame|undefined, selected:Coordinates|null, origin:Coordinates|undefined, radius:number, duration:number, mode:string) {
  const features = (data?.features ?? []).filter(feature => !(frame && feature.properties?.layer === "Traffic")).map(feature=>{
    if(!frame||!origin||feature.properties?.layer!=="Transit"||feature.geometry.type!=="LineString"||
      !intersectsZone(feature.geometry.coordinates,origin,radius))return feature;
    return {...feature,properties:{...feature.properties,modeledDelay:frame.metrics.transitDelay}};
  });
  for (const feature of data?.features??[]) {
    const properties=feature.properties;
    if(feature.geometry.type==="Point"&&properties?.layer==="Sensors"&&properties.online!==false&&
      typeof properties.radius==="number"&&properties.radius>0) {
      const [longitude,latitude]=feature.geometry.coordinates;
      features.push({type:"Feature",geometry:pulseRegion([longitude,latitude],properties.radius),
        properties:{layer:"Sensor coverage",name:properties.name}});
    }
  }
  if (frame) {
    for (const item of frame.flows) {
      features.push({type:"Feature",geometry:{type:"LineString",coordinates:item.coordinates},
        properties:{layer:mode === "Predicted" ? "Predicted congestion" : "Traffic",pressure:item.pressure,id:item.id}});
      if (mode === "Recommended" && item.affected && frame.interventionActive) {
        features.push({type:"Feature",geometry:{type:"LineString",coordinates:item.coordinates},
          properties:{layer:"Intervention paths",pressure:18,id:item.id}});
      }
    }
    if (origin && mode === "Recommended" && frame.interventionActive) features.push({type:"Feature",geometry:{type:"Point",coordinates:origin},
      properties:{layer:"Recommendations",name:"Recommended intervention area"}});
    if (origin) {
      features.push(
        {type:"Feature",geometry:pulseRegion(origin,radius),properties:{layer:"Risk zones",name:"Modeled impact area"}},
        {type:"Feature",geometry:pulseRegion(origin,radius),properties:{layer:"Air quality",
          name:"Modeled emissions change",modeledEmissions:frame.metrics.emissions}},
        {type:"Feature",geometry:{type:"Point",coordinates:origin},properties:{layer:"Incidents",
          name:"Modeled scenario incident",phase:frame.incidentPhase??(frame.minute<=duration?"Active":"Recovery"),
          intensity:frame.incidentIntensity??(frame.minute<=duration ? .8 : .25)}},
      );
    }
  }
  if (selected) features.push({type:"Feature",geometry:{type:"Point",coordinates:selected},
    properties:{layer:"Selection",name:"Selected scenario location"}});
  return {type:"FeatureCollection",features} as GeoJSON.FeatureCollection;
}

function setup(map:MapInstance) {
  map.addSource("city-overlays", {type:"geojson",data:EMPTY});
  map.addSource("city-sensors", {type:"geojson",data:EMPTY,cluster:true,clusterRadius:24,clusterMaxZoom:13});
  const category: ["get", string] = ["get", "layer"];
  const categoryColor = ["match", category, "Traffic", colors.Traffic, ...Object.entries(colors).filter(([layer])=>layer!=="Traffic").flat(), "#58d7ea"] satisfies maplibregl.ExpressionSpecification;
  map.addLayer({id:"air-exposure",type:"heatmap",source:"city-overlays",filter:["==",category,"Air quality"],
    paint:{"heatmap-opacity":.5,"heatmap-radius":45,"heatmap-intensity":.85}});
  map.addLayer({id:"zones",type:"fill",source:"city-overlays",filter:["all",["==",["geometry-type"],"Polygon"],["!=",category,"City boundary"],["!",["has","modeledEmissions"]]],
    paint:{"fill-opacity":.19,"fill-color":categoryColor,"fill-outline-color":categoryColor}});
  map.addLayer({id:"modeled-emissions",type:"fill",source:"city-overlays",filter:["has","modeledEmissions"],
    paint:{"fill-color":["interpolate",["linear"],["get","modeledEmissions"],-15,"#4be1b3",0,"#c2a959",20,"#ff7864"],
      "fill-opacity":.29,"fill-outline-color":"#f9dd93"}});
  map.addLayer({id:"city-boundary",type:"line",source:"city-overlays",
    filter:["all",["==",category,"City boundary"],["==",["geometry-type"],"Polygon"]],
    paint:{"line-color":colors["City boundary"],"line-width":2,"line-dasharray":[3,2],"line-opacity":.76}});
  for (const [id, width, opacity] of [["flow-glow", 13, .12], ["flow", 3.15, .93]] as const) {
    map.addLayer({id,type:"line",source:"city-overlays",filter:["==",["geometry-type"],"LineString"],
      layout:{"line-join":"round","line-cap":"round"},
      paint:{"line-width":width,"line-opacity":opacity,
        "line-color":["case",["has","modeledDelay"],
          ["interpolate",["linear"],["get","modeledDelay"],0,"#ae8bfa",5,"#e1b56a",14,"#fa655f"],
          ["in",category,["literal",["Traffic","Predicted congestion"]]],
          ["interpolate",["linear"],["coalesce",["get","pressure"],35],0,"#2fd3ad",38,"#36dab0",
            63,"#e1b56a",85,"#ed8862",100,"#fa655f"],["to-color",["get","color"],categoryColor]]}}); 
  }
  map.addLayer({id:"map-halos",type:"circle",source:"city-overlays",
    filter:["all",["==",["geometry-type"],"Point"],["in",category,["literal",["Incidents","Selection"]]]],
    paint:{"circle-radius":17,"circle-color":categoryColor,"circle-opacity":.16,"circle-stroke-color":categoryColor,
      "circle-stroke-width":1,"circle-stroke-opacity":.35}});
  map.addLayer({id:"map-points",type:"circle",source:"city-overlays",
    filter:["all",["==",["geometry-type"],"Point"],["!",["in",category,["literal",["Districts","Sensors"]]]]],
    paint:{"circle-radius":["case",["has","intensity"],["+",5,["*",8,["get","intensity"]]],
      ["match",category,"Incidents",7,"Selection",7,4]],"circle-color":categoryColor,
      "circle-opacity":["case",["==",["get","stale"],true],.45,1],
      "circle-stroke-color":"#162436","circle-stroke-width":2}});
  map.addLayer({id:"sensor-dots",type:"circle",source:"city-sensors",
    paint:{"circle-radius":["case",["has","point_count"],8,4],"circle-color":"#7bb8ff","circle-stroke-width":1.5,
      "circle-stroke-color":"#132744","circle-opacity":.9}});
  map.addLayer({id:"district-labels",type:"symbol",source:"city-overlays",filter:["==",category,"Districts"],
    layout:{"text-field":["get","name"],"text-font":["Noto Sans Regular"],"text-size":12,"text-padding":13},
    paint:{"text-color":"#a3b5c8","text-halo-color":"#101923","text-halo-width":1.4}});
}

export default function CityMap({city,data,incidents,selected,select,frame,mode,radius=850,forecastOrigin,duration=60,style,t,expanded,startPicking}:Props) {
  const element = useRef<HTMLDivElement>(null);
  const shell = useRef<HTMLDivElement>(null);
  const map = useRef<MapInstance | null>(null);
  const selection = useRef(select);
  const labels = useRef(t);
  const [enabled,setEnabled] = useState<string[]>(defaultLayers);
  const [layersOpen,setLayersOpen] = useState(false);
  const [picker,setPicker] = useState(!!startPicking);
  const [ready,setReady] = useState(0);
  const [unavailable,setUnavailable] = useState(false);
  const [rotated,setRotated] = useState(false);
  const interaction = useRef(!!startPicking);
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => { selection.current = select; },[select]);
  useEffect(() => { labels.current = t; },[t]);
  useEffect(() => { interaction.current = picker; },[picker]);

  useEffect(() => {
    if (!element.current) return;
    let instance: MapInstance | undefined;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    const markers: maplibregl.Marker[] = [];
    const basemap = style === "local" && city.id !== "debrecen" ? "fiord" : (style ?? (city.id === "debrecen" ? "local" : "fiord"));
    const requested = basemap === "local" ? localStyle : mapStyles[basemap] ?? mapStyles.fiord;
    try {
      instance = new maplibregl.Map({
        container:element.current, style:requested, center:city.center, zoom:city.zoom,
        attributionControl:{compact:true}, minZoom:3, maxZoom:19, maxPitch:70, renderWorldCopies:false,
      });
    } catch {
      const failure = setTimeout(() => setUnavailable(true), 0);
      return () => clearTimeout(failure);
    }
    map.current = instance;
    const active = instance;
    const polygon = new ResizeObserver(() => active.resize());
    polygon.observe(element.current);
    active.on("style.load", () => {
      if (timeout) clearTimeout(timeout);
      if (active.getSource("openmaptiles") && !active.getLayer("city-3d-buildings")) {
        active.addLayer({id:"city-3d-buildings",type:"fill-extrusion",source:"openmaptiles","source-layer":"building",minzoom:14,
          paint:{"fill-extrusion-color":"#738597","fill-extrusion-opacity":.62,
            "fill-extrusion-height":["coalesce",["get","render_height"],6],
            "fill-extrusion-base":["coalesce",["get","render_min_height"],0]}});
      }
      setup(active);
      setUnavailable(false);
      setReady(n => n+1);
      if (!markers.length && city.id === "debrecen") {
        const label = document.createElement("div");
        label.className = "campus-marker";
        const title = document.createElement("b");
        title.textContent = campusLabel.title;
        const subtitle = document.createElement("small");
        subtitle.textContent = campusLabel.subtitle;
        label.append(title,subtitle);
        markers.push(new maplibregl.Marker({element:label,anchor:"bottom-left",offset:[12,10]})
          .setLngLat(city.origin).addTo(active));
      }
    });
    if (basemap !== "local" && city.id === "debrecen") {
      timeout = setTimeout(() => {
        if (!active.isStyleLoaded()) {
          active.setStyle(localStyle);
        }
      }, 3500);
    }
    active.on("click", (event) => {
      if (interaction.current) {
        selection.current([+event.lngLat.lng.toFixed(5),+event.lngLat.lat.toFixed(5)]);
        setPicker(false);
        return;
      }
      const hits = active.queryRenderedFeatures(event.point,{layers:["map-points","sensor-dots","flow","city-boundary","modeled-emissions"].filter(id=>active.getLayer(id))});
      const cluster=hits.find(item=>item.properties?.cluster);
      const sensorSource=active.getSource("city-sensors") as GeoJSONSource|undefined;
      if(cluster&&sensorSource&&cluster.geometry.type==="Point") {
        const [longitude,latitude]=cluster.geometry.coordinates;
        void sensorSource.getClusterExpansionZoom(cluster.properties.cluster_id).then(zoom=>
          active.easeTo({center:[longitude,latitude],zoom,duration:reduce()?0:500})).catch(()=>undefined);
        return;
      }
      const label = hits.find(item => item.properties?.name || item.properties?.id)?.properties;
      if (!label) return;
      const node = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = labels.current(label.name || label.id);
      node.append(strong);
      if (label.location) {
        const location = document.createElement("small");
        location.textContent = label.location;
        node.append(location);
      }
      if(label.approximate||label.stale) {
        const note=document.createElement("small");
        note.textContent=labels.current(label.approximate?"Approximate route between stops":"Stale observation");
        node.append(note);
      }
      for(const [name,value] of [
        ["Modeled transit delay", typeof label.modeledDelay==="number"?label.modeledDelay+" min":""],
        ["Modeled emissions change", typeof label.modeledEmissions==="number"?label.modeledEmissions+"%":""],
        ["Incident phase", label.phase?labels.current(label.phase):""],
      ]) {
        if(!value)continue;
        const note=document.createElement("small");
        note.textContent=labels.current(name)+" · "+value;
        node.append(note);
      }
      new maplibregl.Popup({maxWidth:"240px"}).setLngLat(event.lngLat).setDOMContent(node).addTo(active);
    });
    return () => {
      if (timeout) clearTimeout(timeout);
      polygon.disconnect();
      markers.forEach(marker=>marker.remove());
      active.remove();
      map.current = null;
    };
  }, [city,style]);

  useEffect(() => {
    const active = map.current;
    const src = active?.getSource("city-overlays") as GeoJSONSource|undefined;
    const sensorSrc = active?.getSource("city-sensors") as GeoJSONSource|undefined;
    if (!src || !sensorSrc) return;
    const overlay = overlayData(data,frame,selected,forecastOrigin,radius,duration,mode);
    const visible = new Set([...enabled,"Districts","Selection"]);
    src.setData({type:"FeatureCollection",features:overlay.features.filter(feature =>
      visible.has(feature.properties?.layer) && feature.properties?.layer !== "Sensors")});
    sensorSrc.setData({type:"FeatureCollection", features:enabled.includes("Sensors") ?
      overlay.features.filter((feature)=>feature.properties?.layer === "Sensors" && feature.geometry.type === "Point") : []});
  }, [ready,data,enabled,selected,frame,mode,radius,forecastOrigin,duration]);

  useEffect(() => {
    if (ready && selected) map.current?.easeTo({center:selected,zoom:Math.max(13.45,map.current.getZoom()),duration:reduce()?0:850});
  }, [selected,ready]);

  const toggle = (name:string) => setEnabled(items=>items.includes(name) ? items.filter(item=>item!==name) : [...items,name]);
  const recenter = () => map.current?.easeTo({center:city.center,zoom:city.zoom,bearing:0,pitch:0,duration:reduce()?0:650});
  const rotate = () => {
    map.current?.easeTo({bearing:rotated ? 0 : -22,pitch:rotated ? 0 : 47,duration:reduce()?0:650});
    setRotated(!rotated);
  };
  function fullScreen() {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void shell.current?.requestFullscreen().catch(()=>undefined);
  }
  const trafficIncident = incidents[0];
  const direction = (value:number, positive:string, negative:string)=>Math.abs(value).toFixed(4)+"° "+(value<0?negative:positive);

  return <div ref={shell} className={`map-area ${expanded?"expanded":""} ${picker?"picking":""}`}>
    <div className={`map-fallback ${city.id === "debrecen" ? "debrecen-fallback" : ""}`} aria-hidden="true"/>
    <div ref={element} className="map-canvas" aria-label={`${city.name} ${t("Digital Twin")}`}/>
    {!ready && trafficIncident && city.id === "debrecen" && <span className="fallback-pin" aria-hidden="true"/>}
    <div className="map-top">
      <div className="map-coordinate"><span className="map-coordinate-dot"/>{direction(city.center[1],"N","S")}, {direction(city.center[0],"E","W")}</div>
      <div className="layer-anchor"><button className="map-button" onClick={()=>setLayersOpen(!layersOpen)} aria-expanded={layersOpen}><Layers3 size={15}/>{t("Layers")}</button>
        {layersOpen && <div className="layer-popover"><strong>{t("Map layers")}</strong>{(data?.layers ?? Object.keys(colors)).map(name=><label key={name}>
          <input type="checkbox" checked={enabled.includes(name)} onChange={()=>toggle(name)}/><span className="legend-dot" style={{background:colors[name]}}/>{t(name)}</label>)}</div>}</div>
    </div>
    {picker && <div className="map-hint" role="status">{t("Click the map to set the scenario location.")}</div>}
    {unavailable && <div className="map-hint" role="status">{t("WebGL unavailable · map preview")}</div>}
    <div className="map-zoom" aria-label={t("Map controls")}>
      <button title={t("Zoom in")} aria-label={t("Zoom in")} onClick={()=>map.current?.zoomIn({duration:reduce()?0:250})} disabled={unavailable}><Plus size={17}/></button>
      <button title={t("Zoom out")} aria-label={t("Zoom out")} onClick={()=>map.current?.zoomOut({duration:reduce()?0:250})} disabled={unavailable}><Minus size={17}/></button>
      <button title={t("Recenter map")} aria-label={t("Recenter map")} onClick={recenter} disabled={unavailable}><RotateCcw size={15}/></button>
      <button title={t("Tilt and rotate map")} aria-label={t("Tilt and rotate map")} aria-pressed={rotated} onClick={rotate} disabled={unavailable}><MoveDownRight size={16}/></button>
      <button title={t("Select scenario location")} aria-label={t("Select scenario location")} aria-pressed={picker} onClick={()=>setPicker(!picker)} disabled={unavailable}><Crosshair size={17}/></button>
      <button title={t("Toggle fullscreen")} aria-label={t("Toggle fullscreen")} onClick={fullScreen}><Maximize size={15}/></button>
    </div>
    <div className="map-legend" aria-label={t("Traffic legend")}>
      <span><i style={{background:"#3bd6af"}}/>{t("Clear")}</span><span><i style={{background:"#e2b16a"}}/>{t("Moderate")}</span>
      <span><i style={{background:"#f37d6f"}}/>{t("Congested")}</span>
    </div>
    {frame&&<div className="map-forecast" aria-label={t("Modeled map conditions")}>
      <span>{t("Modeled transit delay")} {frame.metrics.transitDelay} min</span>
      <span>{t("Modeled emissions change")} {frame.metrics.emissions}%</span>
      <span>{t("Incident phase")} {t(frame.incidentPhase??(frame.minute<=duration?"Active":"Recovery"))}</span>
    </div>}
    {!ready && <div className="map-credit"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a></div>}
  </div>;
}

