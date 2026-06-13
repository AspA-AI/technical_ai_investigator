```markdown
# Technical Investigation Report

## Investigation ID: 35
**Upload ID:** dfbcfb9a2aa043e4  
**Status:** Completed

---

## Executive Summary

This report details the investigation into detected anomalies including temperature spikes, pressure drops, vibration spikes, and RPM drops. Historical context reveals five related incidents. The likely root causes are identified as sensor anomaly patterns and degradation of the high-pressure compressor (HPC) and fan under multiple operating conditions. Recommendations for addressing these issues are provided.

---

## Anomaly Findings

### Detected Anomalies
- **Temperature Spike**
- **Pressure Drop**
- **Vibration Spike**
- **RPM Drop**

---

## Historical NASA Evidence

### Related Incidents
1. **Incident ID:** 4063  
   **Similarity:** 0.4678  
   **Failure:** NASA C-MAPSS FD004 turbofan degradation trajectory  
   **Root Cause:** HPC degradation and fan degradation under multiple operating conditions  
   **Resolution:** Inspect compressor and fan assemblies across operating regimes  
   **Summary:** Unit 63 ran for 170 cycles. End-of-life sensor changes were strongest in sensor_9 -316.90, sensor_7 -196.03, sensor_12 -184.61.

2. **Incident ID:** 4138  
   **Similarity:** 0.4651  
   **Failure:** NASA C-MAPSS FD004 turbofan degradation trajectory  
   **Root Cause:** HPC degradation and fan degradation under multiple operating conditions  
   **Resolution:** Inspect compressor and fan assemblies across operating regimes  
   **Summary:** Unit 138 ran for 178 cycles. End-of-life sensor changes were strongest in sensor_9 -722.86, sensor_7 -414.95, sensor_12 -392.66.

3. **Incident ID:** 4143  
   **Similarity:** 0.4641  
   **Failure:** NASA C-MAPSS FD004 turbofan degradation trajectory  
   **Root Cause:** HPC degradation and fan degradation under multiple operating conditions  
   **Resolution:** Inspect compressor and fan assemblies across operating regimes  
   **Summary:** Unit 143 ran for 184 cycles. End-of-life sensor changes were strongest in sensor_13 +359.61, sensor_9 +304.05, sensor_18 +297.00.

4. **Incident ID:** 4073  
   **Similarity:** 0.4621  
   **Failure:** NASA C-MAPSS FD004 turbofan degradation trajectory  
   **Root Cause:** HPC degradation and fan degradation under multiple operating conditions  
   **Resolution:** Inspect compressor and fan assemblies across operating regimes  
   **Summary:** Unit 73 ran for 181 cycles. End-of-life sensor changes were strongest in sensor_9 -735.22, sensor_7 -416.13, sensor_12 -391.81.

5. **Incident ID:** 4176  
   **Similarity:** 0.4619  
   **Failure:** NASA C-MAPSS FD004 turbofan degradation trajectory  
   **Root Cause:** HPC degradation and fan degradation under multiple operating conditions  
   **Resolution:** Inspect compressor and fan assemblies across operating regimes  
   **Summary:** Unit 176 ran for 180 cycles. End-of-life sensor changes were strongest in sensor_9 -707.84, sensor_7 -416.81, sensor_12 -391.81.

---

## Archived GitHub Issue Evidence

### Related Issues
1. **Issue ID:** 4  
   **Similarity:** 0.7303  
   **Failure:** Asset Outage  
   **Root Cause:** Asset Failure Risk: 5cb3ad3be2e049e1  
   **Resolution:** Closed on 2026-06-12  
   **Summary:** [GitHub Issue #4](https://github.com/RYees/factory-maintenance-tracking/issues/4)  
   **Details:** Anomalies detected include temperature spike, pressure drop, vibration spike, and RPM drop. Recommendations include inspecting HPC blades and seals.

2. **Issue ID:** 3  
   **Similarity:** 0.7087  
   **Failure:** Asset Outage  
   **Root Cause:** Asset Failure Risk: 4ec29d3201084887  
   **Resolution:** Closed on 2026-06-12  
   **Summary:** [GitHub Issue #3](https://github.com/RYees/factory-maintenance-tracking/issues/3)  
   **Details:** Anomalies detected include temperature spike, pressure drop, vibration spike, and RPM drop. Recommendations include inspecting HPC blades and seals.

---

## Root Cause Analysis

### Identified Root Causes
1. **Sensor Anomaly Pattern**  
   **Confidence:** 50%  
   **Evidence:** Anomaly signals detected in sensor telemetry.

2. **HPC Degradation and Fan Degradation**  
   **Confidence:** 47%  
   **Evidence:** Matched incidents 4063 and 4138.

3. **HPC Degradation and Fan Degradation**  
   **Confidence:** 46%  
   **Evidence:** Matched incidents 4143, 4073, and 4176.

---

## Recommendations

1. **Inspect High-Pressure Compressor Blades and Seals**
2. **Correlate Findings with Similar Historical Incidents**
3. **Validate the Final Hypothesis with Maintenance and Inspection Records**

---

## Sources

- NASA C-MAPSS FD004 Turbofan Degradation Trajectory Data
- [GitHub Issue #4](https://github.com/RYees/factory-maintenance-tracking/issues/4)
- [GitHub Issue #3](https://github.com/RYees/factory-maintenance-tracking/issues/3)

--- 
```