# HCME Business Questions

Questions that must eventually be answered by HCME/business stakeholders before or during Phase 2. None of these are answered by this specification — every UNKNOWN in `HCME_CONFIRMED_VS_UNKNOWN.md` that a process document needed to route somewhere is routed here.

## BUSINESS

1. What is the authoritative parts master (the source of part numbers, descriptions, fitment data)?
2. Which HCME European depots participate in fulfilment, and what is their relationship to the confirmed global 4-depot regional tier?
3. How is customer-specific pricing handled (which accounts get which pricing, and how is that resolved at order time)?
4. How is allocation performed today, outside of any digital system (i.e., what is the current manual process this platform should reflect or improve on)?
5. Is there a VOR/emergency priority process today, formal or informal?
6. What makes a service job complete — is technician sign-off sufficient, or does the customer also need to confirm?
7. Should split fulfilment (multiple sources covering one request) be offered by default, or only as a fallback?
8. Who is authorised to select a Fulfilment Option — the customer, the dealer, or does it depend on account type?
9. Should partial allocation (less than the requested quantity) be accepted automatically, or must it always be explicitly confirmed?
10. What should happen when a shipment is confirmed lost or a part is confirmed damaged — is a replacement automatic, or does it require new approval?

## DATA

11. What is the authoritative inventory source for each tier (dealer, regional, central)?
12. Which system owns dealer inventory data, and is it queryable in real time?
13. Which system owns pricing, and what inputs does it require (customer, dealer, part, quantity)?
14. Which system owns service job data — is it ConSite, a separate system, or does one not yet exist?
15. What is the dealer master data source (dealer identifier, branch identifier, territory, address, contact)?
16. What is an acceptable "freshness" threshold before inventory data is treated as stale/`UNKNOWN` (see `AVAILABILITY_PROCESS.md`)?
17. How long should an allocation reservation remain `RESERVED` before it expires (see `ALLOCATION_PROCESS.md`)?

## INTEGRATION

18. Which system creates the official order (the system of record once this process hands off)?
19. Which system creates the shipment, and does it differ by carrier or region?
20. How is tracking received — carrier push (webhook/EDI), polling, or manual dealer update?
21. Which APIs/EDI integrations are available to HCME today (beyond the confirmed public Telematics API)?
22. Can dealer stock be queried digitally at all, by any existing HCME or dealer-side system?
23. If/when telemetry (ConSite, the Telematics API) is connected as a future upstream trigger, what event or data model would it use to suggest a part need — without becoming a dependency (see `PHASE_1_DECISIONS.md` §3)?

## SECURITY

24. What authentication model will dealers and customers use to access this platform?
25. What data can external applications (dealers, third-party integrators) legally and contractually access?
26. What audit information must be retained for a completed Fulfilment Request, and for how long?
27. Are there data residency or privacy constraints specific to European customer/dealer data?

## OPERATIONS

28. Which carriers are used today for parts shipment into and within Europe?
29. What are the SLA requirements for each stage (availability check latency, allocation confirmation time, order acceptance time)?
30. What is the escalation process when a source, carrier, or pricing system is unavailable for an extended period (see failure cases 6, 10, 22 in `FAILURE_AND_EXCEPTION_CASES.md`)?
31. Who is the business owner for defining an eventual allocation/VOR priority policy, if HCME decides it wants one?

## How to use this list

Each answered question should update `HCME_CONFIRMED_VS_UNKNOWN.md` (moving the relevant row from UNKNOWN to CONFIRMED with its source), not silently change a process document. Process documents should only be revised once an answer is confirmed and recorded there.
