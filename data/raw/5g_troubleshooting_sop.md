# 5G Troubleshooting SOP

Document ID: DT_5G_SOP_001
Company: Deutsche Telekom
Department: Network Support
Region: Germany
Product: 5G
Access Level: support_agent

## Scope
Use this SOP when a customer reports weak 5G signal, LTE fallback, no mobile data, or degraded service after SIM replacement. This procedure applies to Berlin, Hamburg, Munich, and other German service regions.

## Frontline Checks
1. Confirm the SIM replacement order is completed and the new ICCID is active on the customer account.
2. Verify the tariff includes 5G access and the subscriber profile is provisioned for NR/5G data.
3. Check whether the device supports Deutsche Telekom 5G bands and whether network mode is set to 5G Auto.
4. Confirm APN settings use the approved internet APN and that roaming or private DNS settings are not blocking data.
5. Ask the customer to restart the device, reseat the SIM when physical SIM is used, and reset network settings.
6. Check current network incidents, planned tower maintenance, and local congestion for the customer postcode or Berlin district.

## Berlin SIM Replacement Scenario
When poor 5G signal starts after SIM replacement in Berlin, support must validate SIM provisioning before treating the case as a radio issue. If provisioning is healthy, compare LTE and 5G attachment, request postcode and device model, then check network incident tools for nearby tower alarms.

## Escalation
Escalate to Network Support L2 when SIM provisioning, device compatibility, APN reset, and local incident checks do not resolve the issue. Include MSISDN, ICCID, IMEI, postcode, timestamp, network mode, and screenshots of field-test signal metrics when available.
