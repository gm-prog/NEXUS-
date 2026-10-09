# NEXUS Domain Model

> **Status:** Conceptual design for Phase 1+. Not implemented in Phase 0.

## Core Entities

### Organization (Future Multi-Tenancy)
- `id`: UUID
- `name`: string
- `created_at`: datetime
- **Not implemented in Phase 0**

### Project
- `id`: UUID
- `organization_id`: UUID (future)
- `name`: string
- `description`: string
- `created_at`: datetime
- `settings`: JSON (feature flags, retention, etc.)

### Environment
- `id`: UUID
- `project_id`: UUID
- `name`: string (e.g., "production", "staging", "development")
- `type`: enum (production, staging, development, test)
- `region`: string (optional)

### Service
- `id`: UUID
- `project_id`: UUID
- `name`: string
- `description`: string
- `owner_team`: string (optional)
- `repository_url`: string (optional)
- `service_tier`: enum (critical, high, standard, low)
- `dependencies`: ServiceDependency[]

### ServiceDependency
- `source_service_id`: UUID
- `target_service_id`: UUID
- `type`: enum (http, grpc, message_queue, database, cache, external_api)
- `criticality`: enum (required, optional, fallback)
- `slo_ref`: string (optional)

### Deployment
- `id`: UUID
- `service_id`: UUID
- `environment_id`: UUID
- `commit_sha`: string
- `version`: string (semver or build ID)
- `deployed_at`: datetime (UTC)
- `deployed_by`: string (user or CI system)
- `status`: enum (success, failed, rolled_back)
- `artifact_urls`: string[] (container images, binaries)
- `config_snapshot`: JSON (optional)

### Commit
- `id`: UUID
- `repository_id`: UUID
- `sha`: string
- `short_sha`: string
- `author`: string
- `author_email`: string
- `message`: string
- `committed_at`: datetime (UTC)
- `parents`: string[]
- `changed_files`: CommitFileChange[]
- `linked_pr`: string (optional)

### CommitFileChange
- `path`: string
- `change_type`: enum (added, modified, deleted, renamed)
- `diff_hunk_count`: int (optional)

### Incident
- `id`: UUID
- `project_id`: UUID
- `environment_id`: UUID
- `title`: string
- `description`: string
- `status`: enum (detected, triaged, investigating, identified, remediation_proposed, validating, resolved, failed, aborted, false_positive)
- `severity`: enum (sev1, sev2, sev3, sev4)
- `detected_at`: datetime (UTC)
- `triaged_at`: datetime (optional)
- `identified_at`: datetime (optional)
- `resolved_at`: datetime (optional)
- `primary_service_id`: UUID (optional)
- `affected_service_ids`: UUID[]
- `detection_source`: enum (alert, user_report, automated_correlation)
- `detection_rule_id`: UUID (optional)

### IncidentEvent
- `id`: UUID
- `incident_id`: UUID
- `event_type`: enum (detected, triaged, hypothesis_created, evidence_added, tool_executed, diagnosis_updated, status_changed, remediation_proposed, validation_started, resolved, reopened)
- `actor_type`: enum (system, human, agent)
- `actor_id`: string
- `payload`: JSON
- `created_at`: datetime (UTC)

### TelemetryEvent (Abstract Base)
- `id`: UUID
- `timestamp`: datetime (UTC)
- `service_id`: UUID
- `environment_id`: UUID
- `trace_id`: string (optional)
- `span_id`: string (optional)

### Trace / Span
- `trace_id`: string
- `span_id`: string
- `parent_span_id`: string (optional)
- `service_id`: UUID
- `operation_name`: string
- `start_time`: datetime (UTC)
- `end_time`: datetime (UTC)
- `duration_ms`: int
- `status`: enum (ok, error, unset)
- `attributes`: JSON
- `events`: SpanEvent[]
- `links`: SpanLink[]

### MetricObservation
- `id`: UUID
- `metric_name`: string
- `metric_type`: enum (counter, gauge, histogram, summary)
- `value`: number
- `labels`: JSON (key-value pairs)
- `timestamp`: datetime (UTC)
- `service_id`: UUID
- `environment_id`: UUID

### LogEvent
- `id`: UUID
- `timestamp`: datetime (UTC)
- `level`: enum (trace, debug, info, warn, error, fatal)
- `message`: string
- `structured_fields`: JSON
- `service_id`: UUID
- `environment_id`: UUID
- `trace_id`: string (optional)
- `span_id`: string (optional)

### Evidence
- `id`: UUID (stable, referenced by hypotheses/diagnosis)
- `incident_id`: UUID
- `evidence_type`: enum (metric, log, trace, deployment, commit, runbook, historical_incident, configuration, dependency_status, baseline, verification_result)
- `source`: enum (telemetry_storage, application_state, git_provider, ci_system, runbook_store, manual)
- `source_reference`: string (query ID, trace ID, commit SHA, URL, etc.)
- `event_time`: datetime (UTC) — when the observation occurred
- `collection_time`: datetime (UTC) — when evidence was retrieved/recorded
- `time_window_start`: datetime (UTC) (optional)
- `time_window_end`: datetime (UTC) (optional)
- `service_id`: UUID (optional)
- `environment_id`: UUID (optional)
- `summary`: string (human-readable)
- `data_provenance`: enum (direct_observation, derived_calculation, model_inference, manual_entry)
- `integrity_status`: enum (verified, unverified, corrupted, partial)
- `availability_status`: enum (available, partial, missing, access_denied)
- `raw_data_ref`: string (optional, pointer to raw payload in blob storage)

### Hypothesis
- `id`: UUID
- `incident_id`: UUID
- `title`: string
- `description`: string
- `proposed_by`: enum (human, agent)
- `proposed_by_id`: string
- `status`: enum (proposed, investigating, supported, contradicted, rejected, confirmed)
- `causal_chain`: CausalLink[]
- `supporting_evidence_ids`: UUID[]
- `contradicting_evidence_ids`: UUID[]
- `required_verifications`: VerificationStep[]
- `created_at`: datetime (UTC)
- `updated_at`: datetime (UTC)

### CausalLink
- `from_type`: enum (trigger, mechanism, symptom, impact)
- `from_description`: string
- `to_type`: enum (trigger, mechanism, symptom, impact)
- `to_description`: string
- `evidence_ids`: UUID[]
- `confidence`: number (0.0–1.0)

### VerificationStep
- `id`: UUID
- `description`: string
- `tool_name`: string
- `tool_parameters`: JSON
- `expected_outcome_if_true`: string
- `expected_outcome_if_false`: string
- `status`: enum (pending, executed, passed, failed, inconclusive)
- `result_evidence_id`: UUID (optional)
- `executed_at`: datetime (optional)

### RootCause / Diagnosis
- `id`: UUID
- `incident_id`: UUID
- `root_cause_type`: enum (code_defect, config_error, dependency_failure, resource_exhaustion, capacity_limit, design_flaw, unknown)
- `summary`: string
- `causal_chain`: CausalLink[]
- `primary_evidence_ids`: UUID[]
- `supporting_evidence_ids`: UUID[]
- `contradicting_evidence_ids`: UUID[]
- `confidence`: number (0.0–1.0)
- `uncertainty_rationale`: string
- `contributing_factors`: string[]
- `trigger_change_id`: UUID (optional, deployment or commit)
- `diagnosed_at`: datetime (UTC)
- `diagnosed_by`: enum (human, agent)
- `diagnosed_by_id`: string

### Runbook
- `id`: UUID
- `project_id`: UUID
- `title`: string
- `description`: string
- `applicable_services`: UUID[]
- `applicable_incident_types`: string[]
- `steps`: RunbookStep[]
- `owner_team`: string
- `last_reviewed_at`: datetime (optional)
- `source_url`: string (optional)

### RunbookStep
- `order`: int
- `title`: string
- `description`: string
- `action_type`: enum (check, command, query, decision, notification)
- `action_payload`: JSON
- `expected_result`: string (optional)

### HistoricalIncident
- `id`: UUID
- `incident_id`: UUID (reference to resolved incident)
- `summary`: string
- `root_cause_summary`: string
- `resolution_summary`: string
- `lessons_learned`: string[]
- `tags`: string[]
- `similarity_vector`: number[] (optional, for embedding-based retrieval)

### AgentRun
- `id`: UUID
- `incident_id`: UUID
- `model_id`: string
- `prompt_version`: string
- `tool_set_version`: string
- `status`: enum (running, completed, failed, timeout, aborted)
- `started_at`: datetime (UTC)
- `completed_at`: datetime (optional)
- `total_tool_calls`: int
- `unique_tools_used`: string[]
- `total_latency_ms`: int
- `total_cost_usd`: number (optional)
- `final_diagnosis_id`: UUID (optional)

### ToolCall
- `id`: UUID
- `agent_run_id`: UUID
- `tool_name`: string
- `parameters`: JSON
- `result`: JSON (optional)
- `result_evidence_id`: UUID (optional)
- `status`: enum (success, error, timeout, validation_failed)
- `error_message`: string (optional)
- `started_at`: datetime (UTC)
- `completed_at`: datetime (optional)
- `duration_ms`: int

### RemediationProposal
- `id`: UUID
- `incident_id`: UUID
- `diagnosis_id`: UUID
- `proposed_by`: enum (human, agent)
- `proposed_by_id`: string
- `description`: string
- `code_changes`: CodeChange[]
- `config_changes`: ConfigChange[]
- `infrastructure_changes`: InfraChange[]
- `test_plan`: TestPlan
- `risk_assessment`: string
- `rollback_plan`: string
- `status`: enum (draft, under_review, approved, rejected, superseded)
- `created_at`: datetime (UTC)
- `reviewed_at`: datetime (optional)
- `reviewed_by`: string (optional)

### CodeChange
- `repository_url`: string
- `file_path`: string
- `change_type`: enum (modify, add, delete, rename)
- `diff`: string
- `rationale`: string

### ConfigChange
- `config_key`: string
- `old_value`: string (optional)
- `new_value`: string
- `environment_id`: UUID
- `rationale`: string

### InfraChange
- `resource_type`: string
- `resource_identifier`: string
- `change_description`: string
- `rationale`: string

### TestPlan
- `unit_tests`: string[]
- `integration_tests`: string[]
- `load_tests`: string[]
- `canary_steps`: string[]
- `rollback_verification`: string[]

### RemediationAttempt
- `id`: UUID
- `proposal_id`: UUID
- `sandbox_id`: string
- `status`: enum (pending, running, completed, failed)
- `execution_log`: string
- `test_results`: TestResult[]
- `scan_results`: ScanResult[]
- `artifacts`: Artifact[]
- `started_at`: datetime (UTC)
- `completed_at`: datetime (optional)
- `human_approved`: boolean
- `approved_by`: string (optional)
- `approved_at`: datetime (optional)
- `pr_url`: string (optional)

### EvaluationCase
- `id`: UUID (matches benchmark case_id)
- `schema_version`: string
- `case_file_path`: string
- `description`: string
- `category`: string
- `scenario_type`: enum (single_cause, multi_factor, ambiguous, insufficient_evidence)
- `ground_truth`: GroundTruth
- `agent_visible_bundle`: EvidenceBundle (subset, no ground truth)

### GroundTruth
- `root_cause_type`: string
- `primary_service_id`: string (optional)
- `trigger_change_id`: string (optional)
- `causal_chain`: CausalLink[]
- `ambiguity_note`: string (optional)
- `insufficient_evidence_note`: string (optional)

### EvidenceBundle
- `evidence_items`: Evidence[] (only what agent should see)
- `incident_window`: TimeWindow
- `affected_services`: UUID[]
- `initial_symptoms`: string[]

### EvaluationRun
- `id`: UUID
- `case_id`: UUID
- `agent_run_id`: UUID
- `evaluator_version`: string
- `started_at`: datetime (UTC)
- `completed_at`: datetime (UTC)
- `scores`: EvaluationScores
- `failure_notes`: string (optional)

### EvaluationScores
- `detection`: number (0.0–1.0)
- `service_localization`: number (0.0–1.0)
- `root_cause_accuracy`: number (0.0–1.0)
- `change_attribution`: number (0.0–1.0)
- `evidence_grounding`: number (0.0–1.0)
- `evidence_reference_validity`: number (0.0–1.0)
- `required_evidence_coverage`: number (0.0–1.0)
- `supporting_evidence_coverage`: number (0.0–1.0)
- `contradicting_evidence_coverage`: number (0.0–1.0)
- `causal_chain_correctness`: number (0.0–1.0)
- `false_attribution_rate`: number (0.0–1.0)
- `abstention_quality`: number (0.0–1.0)
- `investigation_coverage`: number (0.0–1.0)
- `tool_efficiency`: number (0.0–1.0)
- `latency_ms`: int
- `cost_usd`: number (optional)
- `remediation_success`: number (0.0–1.0, optional)

## Relationship Summary

```
Organization (1) ──< Project (1) ──< Environment
Project (1) ──< Service
Service (M) ──< ServiceDependency (M) ──> Service
Service (1) ──< Deployment
Deployment (M) ──< Commit (1)
Incident (1) ──< IncidentEvent
Incident (1) ──< Hypothesis
Incident (1) ──< Evidence
Incident (1) ──< Diagnosis
Incident (1) ──< RemediationProposal
AgentRun (1) ──< ToolCall
EvaluationCase (1) ──< EvaluationRun
```

## Source-of-Truth Boundaries

| Domain | Store | Rationale |
|--------|-------|-----------|
| Telemetry (logs, metrics, traces) | Analytical columnar store | High volume, time-series queries, append-only |
| Application state (incidents, hypotheses, evidence refs, eval) | Relational DB | Transactional, complex relationships, updates |
| Raw telemetry payloads | Blob/object storage | Immutable, large, infrequent access |
| Runbooks, documentation | Git/wiki | Versioned, human-editable |
| Evaluation results | Relational DB | Structured, queryable, versioned |

**Key rule:** Not every telemetry record becomes an application-state row. Evidence references point to telemetry storage; they do not duplicate it.