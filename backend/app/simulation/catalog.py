from dataclasses import dataclass


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    summary: str
    recovery: float
    transit: float
    demand: float
    protection: float
    cost: int
    complexity: int
    measure: str
    energy_relief: float = 0


def negotiated_strategy(first, second):
    """Model a split effort between two measures already allowed by the scenario."""

    def blended(key):
        return 0.6 * getattr(first, key) + 0.4 * getattr(second, key)

    return Strategy(
        f"revision-{first.id}-{second.id}",
        "Negotiated intervention",
        "Allocate 60% of the modeled implementation effort to the first measure and 40% to the second.",
        blended("recovery"),
        blended("transit"),
        blended("demand"),
        blended("protection"),
        min(100, max(first.cost, second.cost) + 10),
        min(100, max(first.complexity, second.complexity) + 10),
        "combined",
        blended("energy_relief"),
    )


BASELINE = Strategy(
    "baseline", "Do nothing", "Keep the existing response unchanged.", 0, 0, 0, 0, 0, 0, "baseline"
)
STRATEGIES = {
    "reroute": Strategy(
        "reroute",
        "Diversion and transit priority",
        "Redirect through-traffic and preserve transit capacity around the affected area.",
        0.34,
        0.55,
        0.24,
        0.35,
        28,
        25,
        "routing",
    ),
    "isolate": Strategy(
        "isolate",
        "Temporary access restriction",
        "Restrict general access to the affected corridor and preserve essential access.",
        0.08,
        0.24,
        0.27,
        0.56,
        42,
        47,
        "restriction",
    ),
    "notify": Strategy(
        "notify",
        "Travel advisory and staggered demand",
        "Communicate the disruption and shift avoidable trips away from the peak.",
        0.12,
        0.18,
        0.32,
        0.22,
        14,
        16,
        "demand",
    ),
    "transit": Strategy(
        "transit",
        "Supplemental transit service",
        "Add accessible replacement service and additional transfer capacity.",
        0.1,
        0.76,
        0.18,
        0.17,
        44,
        38,
        "transit",
    ),
    "exposure": Strategy(
        "exposure",
        "Exposure reduction and monitoring",
        "Reduce activity within the affected zone and increase monitoring coverage.",
        0.05,
        0.14,
        0.36,
        0.63,
        39,
        34,
        "restriction",
    ),
    "energy": Strategy(
        "energy",
        "Prioritize essential services",
        "Shift flexible energy demand and reserve capacity for essential facilities.",
        0.18,
        0.2,
        0.27,
        0.62,
        36,
        41,
        "demand",
        1,
    ),
}
PROFILES = {
    "Emergency": ("reroute", "isolate", "notify"),
    "Road Closure": ("reroute", "transit", "notify"),
    "Campus Event": ("notify", "transit", "reroute"),
    "Football Match": ("transit", "notify", "reroute"),
    "Pollution Spike": ("exposure", "notify", "transit"),
    "Severe Weather": ("isolate", "exposure", "transit"),
    "Transit Failure": ("transit", "reroute", "notify"),
    "Construction": ("reroute", "notify", "transit"),
    "Power Outage": ("energy", "notify", "transit"),
    "Public Gathering": ("notify", "transit", "isolate"),
}
