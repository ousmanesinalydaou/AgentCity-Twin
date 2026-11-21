window.agentCityDemo = {
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
  "modelVersion": "network-1.1"
};
