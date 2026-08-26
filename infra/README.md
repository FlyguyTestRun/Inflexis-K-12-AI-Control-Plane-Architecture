# Infrastructure

**Nothing is implemented here yet.** This file records intended shape so that
Phase 1 infrastructure work starts from a decision rather than a blank page.

## Reference deployment

| Concern | Service |
| --- | --- |
| Identity | Entra ID |
| Compute | Azure Container Apps (or AKS at scale) |
| Retrieval | Azure AI Search |
| Relational | Azure Database for PostgreSQL |
| Object storage | Azure Blob Storage |
| Secrets | Key Vault, accessed by managed identity |
| Models | Azure OpenAI / Microsoft Foundry |
| Observability | Azure Monitor |
| Audit | Append-only store (immutable table or Monitor) |

## Non-negotiables

- **Managed identity throughout.** No connection strings, no keys in
  configuration.
- **Private endpoints** for search, storage, and database. No public datastore
  exposure.
- **Per-tenant isolation decision recorded**: index-per-tenant versus filtered
  shared index is a real trade-off (cost and operational overhead against blast
  radius) and must be an explicit, documented choice rather than a default.
- **Environments:** dev, staging (synthetic data only), production.
- **No real district data outside production.**

## Planned layout

```
infra/
  bicep/  or  terraform/
    main
    search
    storage
    postgres
    keyvault
    monitoring
    container-app
  environments/
    dev/
    staging/
    prod/
```

See [`../docs/implementation/phase-1-plan.md`](../docs/implementation/phase-1-plan.md)
workstream W8.
