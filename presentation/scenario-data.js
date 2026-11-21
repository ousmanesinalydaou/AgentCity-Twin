window.agentCityScenarios = [
  {
    "id": "university-accident",
    "label": "University corridor accident",
    "kind": "Emergency",
    "location": "University of Debrecen",
    "time": "17:00",
    "duration": 60,
    "severity": 4,
    "population": 1200,
    "radius": 850,
    "brief": "Compare diversion and transit priority with restricting access near campus.",
    "highlight": "safetyRisk",
    "name": "Diversion and transit priority",
    "mode": "Simulated",
    "scenario": {
      "location": "University of Debrecen",
      "startsAt": "17:00",
      "duration": 60,
      "severity": 4,
      "seed": 42
    },
    "scores": {
      "baseline": 41.97,
      "recommended": 67.17
    },
    "frames": [
      {
        "minute": 0,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 10.9,
          "transitDelay": 10.7,
          "emissions": 31,
          "safetyRisk": 89.1,
          "energyLoad": 85,
          "trips": 2514,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 86.1,
          "travelDelay": 7.1,
          "transitDelay": 6.8,
          "emissions": 21.7,
          "safetyRisk": 80.1,
          "energyLoad": 85,
          "trips": 2387,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 15,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 9.8,
          "transitDelay": 10.1,
          "emissions": 28.9,
          "safetyRisk": 88.7,
          "energyLoad": 85,
          "trips": 2427,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 64.1,
          "travelDelay": 3.4,
          "transitDelay": 1.8,
          "emissions": 11.1,
          "safetyRisk": 66.5,
          "energyLoad": 85,
          "trips": 2104,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 30,
        "phase": "Active",
        "baseline": {
          "congestion": 98.3,
          "travelDelay": 8.7,
          "transitDelay": 9.4,
          "emissions": 27,
          "safetyRisk": 88.4,
          "energyLoad": 85,
          "trips": 2339,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 57.3,
          "travelDelay": 2.2,
          "transitDelay": 0,
          "emissions": 6.4,
          "safetyRisk": 58.2,
          "energyLoad": 85,
          "trips": 1902,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 60,
        "phase": "Active",
        "baseline": {
          "congestion": 89.4,
          "travelDelay": 8.5,
          "transitDelay": 9.3,
          "emissions": 26.5,
          "safetyRisk": 87.3,
          "energyLoad": 85,
          "trips": 2163,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 52.5,
          "travelDelay": 1.8,
          "transitDelay": 0,
          "emissions": 5.6,
          "safetyRisk": 57.7,
          "energyLoad": 85,
          "trips": 1759,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 120,
        "phase": "Recovery",
        "baseline": {
          "congestion": 37.5,
          "travelDelay": 1.1,
          "transitDelay": 2.1,
          "emissions": 5.7,
          "safetyRisk": 46.8,
          "energyLoad": 71.8,
          "trips": 1427,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 28.9,
          "travelDelay": 0.6,
          "transitDelay": 0,
          "emissions": -3.5,
          "safetyRisk": 19.6,
          "energyLoad": 71.8,
          "trips": 1160,
          "sensorCoverage": 92
        }
      }
    ],
    "negotiation": {
      "first": "Diversion and transit priority",
      "second": "Temporary access restriction",
      "score": 64.73,
      "selected": false
    },
    "specialists": [
      {
        "name": "Traffic Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Mobility Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Environment Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Safety Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Campus Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      }
    ],
    "modelVersion": "network-1.1",
    "summary": "Redirect through-traffic and preserve transit capacity around the affected area.",
    "images": {
      "forecast": "02-forecast.jpg",
      "comparison": "03-comparison.jpg",
      "explanation": "04-explanation.jpg",
      "audit": "05-audit.jpg"
    }
  },
  {
    "id": "tram-disruption",
    "label": "Tram breakdown downtown",
    "kind": "Transit Failure",
    "location": "Debrecen city center",
    "time": "18:10",
    "duration": 60,
    "severity": 4,
    "population": 2300,
    "radius": 1100,
    "brief": "Compare replacement service with demand management when road diversion is unavailable.",
    "highlight": "transitDelay",
    "name": "Travel advisory and staggered demand",
    "summary": "Communicate the disruption and shift avoidable trips away from the peak.",
    "mode": "Simulated",
    "scenario": {
      "location": "Debrecen city center",
      "startsAt": "18:10",
      "duration": 60,
      "severity": 4,
      "seed": 42
    },
    "scores": {
      "baseline": 47.76,
      "recommended": 60.77
    },
    "frames": [
      {
        "minute": 0,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 6.3,
          "transitDelay": 7.9,
          "emissions": 22.4,
          "safetyRisk": 91.3,
          "energyLoad": 85,
          "trips": 2565,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 100,
          "travelDelay": 4.6,
          "transitDelay": 6.3,
          "emissions": 16.1,
          "safetyRisk": 85.4,
          "energyLoad": 85,
          "trips": 2396,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 15,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 5.7,
          "transitDelay": 7.5,
          "emissions": 21.2,
          "safetyRisk": 90.9,
          "energyLoad": 85,
          "trips": 2476,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 86.2,
          "travelDelay": 6.1,
          "transitDelay": 6.4,
          "emissions": 14.2,
          "safetyRisk": 75.7,
          "energyLoad": 85,
          "trips": 2046,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 30,
        "phase": "Active",
        "baseline": {
          "congestion": 83.7,
          "travelDelay": 4.4,
          "transitDelay": 6.8,
          "emissions": 18.8,
          "safetyRisk": 87.4,
          "energyLoad": 85,
          "trips": 1878,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 54.3,
          "travelDelay": 2.8,
          "transitDelay": 3.8,
          "emissions": 4.8,
          "safetyRisk": 67.5,
          "energyLoad": 85,
          "trips": 1419,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 60,
        "phase": "Active",
        "baseline": {
          "congestion": 76.5,
          "travelDelay": 3.5,
          "transitDelay": 6.2,
          "emissions": 17.1,
          "safetyRisk": 86.7,
          "energyLoad": 85,
          "trips": 1737,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 49.6,
          "travelDelay": 2.2,
          "transitDelay": 3.4,
          "emissions": 3.7,
          "safetyRisk": 67,
          "energyLoad": 85,
          "trips": 1313,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 120,
        "phase": "Recovery",
        "baseline": {
          "congestion": 39.8,
          "travelDelay": 1.5,
          "transitDelay": 2.3,
          "emissions": 6.5,
          "safetyRisk": 47,
          "energyLoad": 71.8,
          "trips": 1456,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 29,
          "travelDelay": 0.7,
          "transitDelay": 0,
          "emissions": -6.1,
          "safetyRisk": 29.3,
          "energyLoad": 71.8,
          "trips": 1100,
          "sensorCoverage": 92
        }
      }
    ],
    "negotiation": {
      "first": "Travel advisory and staggered demand",
      "second": "Supplemental transit service",
      "score": 57.29,
      "selected": false
    },
    "specialists": [
      {
        "name": "Traffic Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Mobility Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Communication Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      }
    ],
    "modelVersion": "network-1.1",
    "restrictions": "No reroute",
    "images": {
      "forecast": "tram-disruption-forecast.jpg",
      "comparison": "tram-disruption-comparison.jpg"
    }
  },
  {
    "id": "stadium-egress",
    "label": "Stadium departure surge",
    "kind": "Football Match",
    "location": "Nagyerdei Stadion",
    "time": "21:45",
    "duration": 75,
    "severity": 3,
    "population": 18000,
    "radius": 1400,
    "brief": "Compare staggered departures and extra transit after a large evening match.",
    "highlight": "congestion",
    "name": "Travel advisory and staggered demand",
    "summary": "Communicate the disruption and shift avoidable trips away from the peak.",
    "mode": "Simulated",
    "scenario": {
      "location": "Nagyerdei Stadion",
      "startsAt": "21:45",
      "duration": 75,
      "severity": 3,
      "seed": 42
    },
    "scores": {
      "baseline": 64.57,
      "recommended": 73.95
    },
    "frames": [
      {
        "minute": 0,
        "phase": "Active",
        "baseline": {
          "congestion": 66.1,
          "travelDelay": 3.4,
          "transitDelay": 5.1,
          "emissions": 14.3,
          "safetyRisk": 72,
          "energyLoad": 80,
          "trips": 2146,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 60.6,
          "travelDelay": 2.8,
          "transitDelay": 4.2,
          "emissions": 10.2,
          "safetyRisk": 66.9,
          "energyLoad": 80,
          "trips": 2013,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 15,
        "phase": "Active",
        "baseline": {
          "congestion": 38.9,
          "travelDelay": 1.3,
          "transitDelay": 3.8,
          "emissions": 10.2,
          "safetyRisk": 68.9,
          "energyLoad": 80,
          "trips": 1291,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 30.8,
          "travelDelay": 0.6,
          "transitDelay": 2,
          "emissions": 1.2,
          "safetyRisk": 56.3,
          "energyLoad": 80,
          "trips": 1080,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 30,
        "phase": "Active",
        "baseline": {
          "congestion": 37.3,
          "travelDelay": 1.1,
          "transitDelay": 3.7,
          "emissions": 9.8,
          "safetyRisk": 68.8,
          "energyLoad": 80,
          "trips": 1245,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 26.8,
          "travelDelay": 0.5,
          "transitDelay": 1.3,
          "emissions": -2.2,
          "safetyRisk": 51,
          "energyLoad": 80,
          "trips": 958,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 60,
        "phase": "Active",
        "baseline": {
          "congestion": 34.3,
          "travelDelay": 0.8,
          "transitDelay": 3.5,
          "emissions": 9.4,
          "safetyRisk": 68.4,
          "energyLoad": 80,
          "trips": 1151,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 25.5,
          "travelDelay": 1.2,
          "transitDelay": 1.8,
          "emissions": -0.8,
          "safetyRisk": 50.7,
          "energyLoad": 80,
          "trips": 887,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 120,
        "phase": "Recovery",
        "baseline": {
          "congestion": 23.6,
          "travelDelay": 0.4,
          "transitDelay": 1.2,
          "emissions": 3.4,
          "safetyRisk": 40.6,
          "energyLoad": 70.1,
          "trips": 965,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 18.2,
          "travelDelay": 0.6,
          "transitDelay": 0,
          "emissions": -7,
          "safetyRisk": 23.4,
          "energyLoad": 70.1,
          "trips": 743,
          "sensorCoverage": 92
        }
      }
    ],
    "negotiation": {
      "first": "Travel advisory and staggered demand",
      "second": "Supplemental transit service",
      "score": 70.54,
      "selected": false
    },
    "specialists": [
      {
        "name": "Traffic Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Mobility Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Safety Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Communication Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      }
    ],
    "modelVersion": "network-1.1",
    "restrictions": "No reroute",
    "images": {
      "forecast": "stadium-egress-forecast.jpg",
      "comparison": "stadium-egress-comparison.jpg"
    }
  },
  {
    "id": "air-quality-alert",
    "label": "Morning air-quality alert",
    "kind": "Pollution Spike",
    "location": "West Debrecen",
    "time": "08:00",
    "duration": 120,
    "severity": 5,
    "population": 6400,
    "radius": 1850,
    "brief": "Show how exposure reduction and monitoring compare with mobility interventions.",
    "highlight": "emissions",
    "name": "Exposure reduction and monitoring",
    "summary": "Reduce activity within the affected zone and increase monitoring coverage.",
    "mode": "Simulated",
    "scenario": {
      "location": "West Debrecen",
      "startsAt": "08:00",
      "duration": 120,
      "severity": 5,
      "seed": 42
    },
    "scores": {
      "baseline": 40.98,
      "recommended": 59.57
    },
    "frames": [
      {
        "minute": 0,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 6.1,
          "transitDelay": 8.8,
          "emissions": 24.6,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2645,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 100,
          "travelDelay": 5.5,
          "transitDelay": 8,
          "emissions": 20.2,
          "safetyRisk": 90,
          "energyLoad": 90,
          "trips": 2455,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 15,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 5.5,
          "transitDelay": 8.4,
          "emissions": 23.4,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2553,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 87.3,
          "travelDelay": 3.3,
          "transitDelay": 5.9,
          "emissions": 10.5,
          "safetyRisk": 67.9,
          "energyLoad": 90,
          "trips": 2069,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 30,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 5.6,
          "transitDelay": 8.5,
          "emissions": 23.6,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2461,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 78.7,
          "travelDelay": 2.4,
          "transitDelay": 5,
          "emissions": 5.4,
          "safetyRisk": 53.4,
          "energyLoad": 90,
          "trips": 1805,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 60,
        "phase": "Active",
        "baseline": {
          "congestion": 94.5,
          "travelDelay": 4.4,
          "transitDelay": 7.7,
          "emissions": 21.4,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2276,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 74.9,
          "travelDelay": 2.5,
          "transitDelay": 5,
          "emissions": 5.5,
          "safetyRisk": 52.8,
          "energyLoad": 90,
          "trips": 1670,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 120,
        "phase": "Active",
        "baseline": {
          "congestion": 68.4,
          "travelDelay": 1.9,
          "transitDelay": 6.2,
          "emissions": 16.6,
          "safetyRisk": 99.4,
          "energyLoad": 90,
          "trips": 1501,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 48.7,
          "travelDelay": 1.1,
          "transitDelay": 4.2,
          "emissions": 2.9,
          "safetyRisk": 49.8,
          "energyLoad": 90,
          "trips": 1101,
          "sensorCoverage": 92
        }
      }
    ],
    "negotiation": null,
    "specialists": [
      {
        "name": "Environment Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Safety Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Sensor Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      }
    ],
    "modelVersion": "network-1.1",
    "restrictions": "",
    "images": {
      "forecast": "air-quality-alert-forecast.jpg",
      "comparison": "air-quality-alert-comparison.jpg"
    }
  },
  {
    "id": "essential-power",
    "label": "Power outage and essential services",
    "kind": "Power Outage",
    "location": "East Debrecen",
    "time": "19:00",
    "duration": 90,
    "severity": 5,
    "population": 7500,
    "radius": 1700,
    "brief": "Compare essential-service priority with mobility responses during an outage.",
    "highlight": "energyLoad",
    "name": "Prioritize essential services",
    "summary": "Shift flexible energy demand and reserve capacity for essential facilities.",
    "mode": "Simulated",
    "scenario": {
      "location": "East Debrecen",
      "startsAt": "19:00",
      "duration": 90,
      "severity": 5,
      "seed": 42
    },
    "scores": {
      "baseline": 40.36,
      "recommended": 60.59
    },
    "frames": [
      {
        "minute": 0,
        "phase": "Active",
        "baseline": {
          "congestion": 100,
          "travelDelay": 6.8,
          "transitDelay": 9.2,
          "emissions": 25.9,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2092,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 95.3,
          "travelDelay": 5.6,
          "transitDelay": 7.9,
          "emissions": 21.2,
          "safetyRisk": 89.5,
          "energyLoad": 83.2,
          "trips": 1979,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 15,
        "phase": "Active",
        "baseline": {
          "congestion": 98,
          "travelDelay": 6.1,
          "transitDelay": 8.8,
          "emissions": 24.6,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 2019,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 81.1,
          "travelDelay": 5.2,
          "transitDelay": 6.7,
          "emissions": 16.4,
          "safetyRisk": 67.2,
          "energyLoad": 72.2,
          "trips": 1733,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 30,
        "phase": "Active",
        "baseline": {
          "congestion": 94.9,
          "travelDelay": 7.7,
          "transitDelay": 9.7,
          "emissions": 27.6,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 1946,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 63.8,
          "travelDelay": 4.8,
          "transitDelay": 5.7,
          "emissions": 12.9,
          "safetyRisk": 51.7,
          "energyLoad": 65,
          "trips": 1559,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 60,
        "phase": "Active",
        "baseline": {
          "congestion": 86.1,
          "travelDelay": 6.1,
          "transitDelay": 8.8,
          "emissions": 24.5,
          "safetyRisk": 100,
          "energyLoad": 90,
          "trips": 1800,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 58,
          "travelDelay": 3.8,
          "transitDelay": 5.1,
          "emissions": 11,
          "safetyRisk": 51.2,
          "energyLoad": 65,
          "trips": 1442,
          "sensorCoverage": 92
        }
      },
      {
        "minute": 120,
        "phase": "Recovery",
        "baseline": {
          "congestion": 40.3,
          "travelDelay": 1.3,
          "transitDelay": 2.5,
          "emissions": 6.9,
          "safetyRisk": 51.7,
          "energyLoad": 73.5,
          "trips": 1508,
          "sensorCoverage": 92
        },
        "recommended": {
          "congestion": 30.8,
          "travelDelay": 0.7,
          "transitDelay": 0,
          "emissions": -3.4,
          "safetyRisk": 4.1,
          "energyLoad": 48.5,
          "trips": 1208,
          "sensorCoverage": 92
        }
      }
    ],
    "negotiation": null,
    "specialists": [
      {
        "name": "Safety Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Energy Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Sensor Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      },
      {
        "name": "Communication Agent",
        "model": "prism-ml/bonsai-27b",
        "provider": "lm-studio"
      }
    ],
    "modelVersion": "network-1.1",
    "restrictions": "",
    "images": {
      "forecast": "essential-power-forecast.jpg",
      "comparison": "essential-power-comparison.jpg"
    }
  }
];
