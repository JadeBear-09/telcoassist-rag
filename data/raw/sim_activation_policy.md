# SIM Activation Policy

Document ID: DT_SIM_POL_048
Company: Deutsche Telekom
Department: Support
Region: Germany
Product: SIM
Access Level: support_agent

## Policy
SIM replacement must complete account verification, ICCID binding, fraud check, and service-profile propagation before support closes the case. New SIM cards may show voice service before packet data provisioning has fully propagated.

## Troubleshooting
If mobile data fails after SIM replacement, support must verify ICCID status, refresh subscriber provisioning, confirm 5G entitlement, and force a network registration retry. Do not replace the SIM again until provisioning status and device compatibility are confirmed.

## Escalation
Escalate to SIM Provisioning L2 if ICCID status remains pending, profile refresh fails, or data service remains inactive after the registration retry.
