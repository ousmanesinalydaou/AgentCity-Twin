# Troubleshooting

| Symptom | Check |
|---|---|
| Browser reports a rejected origin | Match `APP_ORIGIN` to the URL in the address bar, including the port. Restart the backend after changing it. |
| Workspace reports service unavailable | Check `/api/v1/health`, frontend proxy configuration, database health, and migration logs. |
| Docker cannot allocate a network | Set `AGENTCITY_DOCKER_SUBNET` to a free CIDR. Avoid pruning other projects' networks. |
| Map tiles are blank | Try the local Debrecen style. Check WebGL support and OpenFreeMap connectivity for online styles. |
| Provider test fails | Confirm credential, API root, deployment ID, server-approved origin, and workspace cloud policy. |
| A run has no graph | Configure city road nodes, edges, and connected demand pairs before running a simulation. |
| Verification message is missing | Confirm SMTP configuration and SMTP server delivery logs. |

