import Image from "next/image";
import type { Translate } from "@/i18n";
import type { Run } from "@/lib/types";

export function PrintReport({run,t}: {run:Run;t:Translate}) {
  const result=run.result;
  if(!result)return null;
  const {scenario}=run;
  return <div className="print-report">
    <h2>{run.title}</h2>
    <p>{scenario.location} · {t(scenario.kind)} · {scenario.duration} min · {t("Simulated data")}</p>
    <p>{scenario.description}</p>
    <p>{t("Data source")} · {result.source} · {t(result.freshness)}</p>
    <p>{t("Recommended strategy")} · {t(result.recommendation.name)} · {result.recommendation.score.toFixed(1)}/100 · {Math.round(result.confidence*100)}% {t("confidence")}</p>
    {scenario.city_id==="debrecen"&&<figure><Image alt={t("Debrecen basemap")} src="/maps/debrecen.webp" width={600} height={384}/>
       <figcaption>© OpenStreetMap contributors · OpenFreeMap</figcaption></figure>}
    <table className="comparison-table"><thead><tr><th>{t("Strategy ranking")}</th><th>{t("Score")}</th>
       <th>{t("Congestion")} (+30m)</th><th>{t("Transit delay")} (+30m)</th><th>{t("Safety risk")} (+30m)</th></tr></thead>
      <tbody>{result.strategies.map(row=><tr key={row.id}><th>{t(row.name)}</th><td>{row.score}</td>
        <td>{row.timeline[2].metrics.congestion}/100</td><td>{row.timeline[2].metrics.transitDelay} min</td>
        <td>{row.timeline[2].metrics.safetyRisk}/100</td></tr>)}</tbody></table>
    <h3>{t("Agent consensus and disagreements")}</h3><ul>{result.messages.map(item=><li key={item.agent}><b>{t(item.name)}</b> · {t(item.summary)} · {item.evidence}</li>)}</ul>
    <h3>{t("Assumptions and limitations")}</h3><ul>{[...result.assumptions,...result.limitations].map(item=><li key={item}>{t(item)}</li>)}</ul>
    <p>{t("Simulation seed")} {result.seed} · {result.model_version}</p>
    {run.approval&&<p>{t("Recorded operator review")} · {run.approval.decision} · {run.approval.actor} · {run.approval.note}</p>}
    <h3>{t("Audit trace")}</h3><ol>{run.events.map(item=><li key={item.seq}>{item.time} · {item.stage} · {item.text}</li>)}</ol>
  </div>;
}

