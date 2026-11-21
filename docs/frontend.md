# Frontend

`frontend/src/app` contains the Next.js entry points and responsive style layers. `components` covers the command center, map, scenario forms, reports, and settings. Reusable requests and workspace subscriptions are in `lib`. The dashboard uses URL query state for navigation and routes API traffic through Next.js rewrites. React imports MapLibre dynamically in the client.

Status, audit events, and historical readings are conveyed as text alongside color. Keyboard-accessible controls, modal dialogs, responsive layouts, a light theme, and reduced-motion preferences are supported. On narrow screens, open sidebar navigation using the menu control.

