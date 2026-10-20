// Package model defines the sanitized DTO types that exactly match
// docs/architecture/p8c/openapi.json (additionalProperties=false, required
// fields, explicit null via pointers). No raw Kubernetes object (spec.env,
// commands, volumes, annotations, secret refs) is ever serialized.
package model

// ---- common envelope -------------------------------------------------------

// Envelope is the common wrapper for every 200 response.
type Envelope struct {
	RequestID   string         `json:"requestId"`
	GeneratedAt string         `json:"generatedAt"`
	ObservedAt  *string        `json:"observedAt"`
	Freshness   string         `json:"freshness"` // fresh|stale|unavailable
	Partial     bool           `json:"partial"`
	Sources     []SourceStatus `json:"sources"`
	Data        any            `json:"data"`
	Warnings    []Warning      `json:"warnings"`
	NextCursor  *string        `json:"nextCursor"`
}

// SourceStatus describes one collection source's state.
type SourceStatus struct {
	ID         string   `json:"id"`
	State      string   `json:"state"` // ok|error|unsupported
	ObservedAt *string  `json:"observedAt"`
	AgeSeconds *float64 `json:"ageSeconds"`
	ErrorCode  *string  `json:"errorCode"`
}

// Warning is a structured, bounded warning entry.
type Warning struct {
	Code     string `json:"code"`
	Severity string `json:"severity"` // normal|warning|critical
	Message  string `json:"message"`
	Source   string `json:"source"`
}

// Condition is a sanitized Kubernetes/CNPG condition.
type Condition struct {
	Type               string  `json:"type"`
	Status             string  `json:"status"` // True|False|Unknown
	Reason             *string `json:"reason"`
	LastTransitionTime *string `json:"lastTransitionTime"`
	ObservedGeneration *int64  `json:"observedGeneration"`
}

// ---- /health ----------------------------------------------------------------

// Health is the /health data object.
type Health struct {
	Status                string   `json:"status"` // healthy|warning|critical|unknown
	BuildRevision         string   `json:"buildRevision"`
	ApplicationDb         string   `json:"applicationDb"` // connected|disconnected|unknown
	SchemaVersion         *int64   `json:"schemaVersion"`
	CollectorState        string   `json:"collectorState"` // starting|running|degraded|stopped
	PersistenceLagSeconds *float64 `json:"persistenceLagSeconds"`
	DataLoss              bool     `json:"dataLoss"`
}

// ---- /summary ---------------------------------------------------------------

type Subsystem struct {
	ID         string  `json:"id"`
	Health     string  `json:"health"`
	Scope      string  `json:"scope"`
	ObservedAt *string `json:"observedAt"`
	Message    string  `json:"message"`
}

type Counts struct {
	NodesObserved   *int64 `json:"nodesObserved"`
	NodesReady      *int64 `json:"nodesReady"`
	NodesExpected   int64  `json:"nodesExpected"`
	PostgresDesired *int64 `json:"postgresDesired"`
	PostgresReady   *int64 `json:"postgresReady"`
	PodsObserved    *int64 `json:"podsObserved"`
	PodsReady       *int64 `json:"podsReady"`
	PvcObserved     *int64 `json:"pvcObserved"`
	PvcBound        *int64 `json:"pvcBound"`
}

type Summary struct {
	Overall    string      `json:"overall"`
	Counts     Counts      `json:"counts"`
	Subsystems []Subsystem `json:"subsystems"`
	Alerts     []Warning   `json:"alerts"`
	Coverage   string      `json:"coverage"`
}

// ---- /nodes ------------------------------------------------------------------

type Node struct {
	Name                  string      `json:"name"`
	UID                   string      `json:"uid"`
	Ready                 string      `json:"ready"` // True|False|Unknown
	Health                string      `json:"health"`
	Conditions            []Condition `json:"conditions"`
	CapacityCpuCores      *float64    `json:"capacityCpuCores"`
	AllocatableCpuCores   *float64    `json:"allocatableCpuCores"`
	CapacityMemoryBytes   *int64      `json:"capacityMemoryBytes"`
	AllocatableMemoryBytes *int64     `json:"allocatableMemoryBytes"`
}

// ---- /workloads ---------------------------------------------------------------

type Workload struct {
	Name       string      `json:"name"`
	Namespace  string      `json:"namespace"`
	UID        string      `json:"uid"`
	Kind       string      `json:"kind"`
	Health     string      `json:"health"`
	Desired    *int32      `json:"desired"`
	Ready      *int32      `json:"ready"`
	Active     *int32      `json:"active"`
	Succeeded  *int32      `json:"succeeded"`
	Failed     *int32      `json:"failed"`
	Suspended  *bool       `json:"suspended"`
	Conditions []Condition `json:"conditions"`
}

// ---- /pods ---------------------------------------------------------------------

type Pod struct {
	Name            string  `json:"name"`
	Namespace       string  `json:"namespace"`
	UID             string  `json:"uid"`
	NodeName        *string `json:"nodeName"`
	Phase           string  `json:"phase"`
	ReadyContainers int32   `json:"readyContainers"`
	TotalContainers int32   `json:"totalContainers"`
	RestartCount    int32   `json:"restartCount"`
	Health          string  `json:"health"`
}

// ---- /services ------------------------------------------------------------------

type ServicePort struct {
	Name     *string `json:"name"`
	Port     int32   `json:"port"`
	Protocol string  `json:"protocol"`
}

type Service struct {
	Name           string        `json:"name"`
	Namespace      string        `json:"namespace"`
	UID            string        `json:"uid"`
	Type           string        `json:"type"`
	Ports          []ServicePort `json:"ports"`
	ReadyEndpoints *int32        `json:"readyEndpoints"`
	Health         string        `json:"health"`
}

// ---- /storage --------------------------------------------------------------------

type StorageItem struct {
	Kind                 string  `json:"kind"`
	Name                 string  `json:"name"`
	Namespace            *string `json:"namespace"`
	UID                  string  `json:"uid"`
	Phase                *string `json:"phase"`
	StorageClass         *string `json:"storageClass"`
	CapacityBytes        *int64  `json:"capacityBytes"`
	RequestedBytes       *int64  `json:"requestedBytes"`
	SnapshotReadyToUse   *bool   `json:"snapshotReadyToUse"`
	SnapshotCreationTime *string `json:"snapshotCreationTime"`
	Health               string  `json:"health"`
}

type Storage struct {
	Scope             string        `json:"scope"`
	DrbdDirectHealth  string        `json:"drbdDirectHealth"`
	Items             []StorageItem `json:"items"`
}

// ---- /backups ---------------------------------------------------------------------

type BackupRecord struct {
	Name          string  `json:"name"`
	Namespace     string  `json:"namespace"`
	Phase         *string `json:"phase"`
	StartedAt     *string `json:"startedAt"`
	CompletedAt   *string `json:"completedAt"`
	WarningsCount *int32  `json:"warningsCount"`
	ErrorsCount   *int32  `json:"errorsCount"`
	Health        string  `json:"health"`
}

type BackupStorageLocation struct {
	Name               string  `json:"name"`
	Namespace          string  `json:"namespace"`
	Phase              *string `json:"phase"`
	LastValidationTime *string `json:"lastValidationTime"`
	Health             string  `json:"health"`
}

type PolicyGap struct {
	ID          string `json:"id"`
	Status      string `json:"status"`
	Explanation string `json:"explanation"`
}

type BarmanSample struct {
	SampledAt                        *string  `json:"sampledAt"`
	ExporterInstance                 *string  `json:"exporterInstance"`
	Scope                            string   `json:"scope"`
	LastAvailableBackupTimestamp     *float64 `json:"lastAvailableBackupTimestamp"`
	FirstRecoverabilityPointTimestamp *float64 `json:"firstRecoverabilityPointTimestamp"`
	LastFailedBackupTimestamp        *float64 `json:"lastFailedBackupTimestamp"`
}

type Wal struct {
	State                          string     `json:"state"`
	ContinuousArchiving            *Condition `json:"continuousArchiving"`
	ConfiguredArchiveTimeoutSeconds *int32    `json:"configuredArchiveTimeoutSeconds"`
	MeasuredRpoSeconds             *float64   `json:"measuredRpoSeconds"` // MUST be null in P8C
	ExpectedArchiveTimeoutSeconds  int32      `json:"expectedArchiveTimeoutSeconds"`
}

type PostgresBackups struct {
	Health                     string         `json:"health"`
	Cluster                    string         `json:"cluster"`
	ObjectStore                string         `json:"objectStore"`
	Schedule                   *string        `json:"schedule"`
	Target                     *string        `json:"target"`
	ScheduledBackupObserved    bool           `json:"scheduledBackupObserved"`
	LastSuccessfulBackupAt     *string        `json:"lastSuccessfulBackupAt"`
	SuccessfulBackupsObserved  int32          `json:"successfulBackupsObserved"`
	CollectionTruncated        bool           `json:"collectionTruncated"`
	Backups                    []BackupRecord `json:"backups"`
	Wal                        Wal            `json:"wal"`
	Barman                     BarmanSample   `json:"barman"`
	ExpectedSchedule           string         `json:"expectedSchedule"`
	ExpectedTarget             string         `json:"expectedTarget"`
}

type VeleroBackups struct {
	Health              string                  `json:"health"`
	CollectionTruncated bool                    `json:"collectionTruncated"`
	Locations           []BackupStorageLocation `json:"locations"`
	Backups             []BackupRecord          `json:"backups"`
	Restores            []BackupRecord          `json:"restores"`
}

type Backups struct {
	Velero     VeleroBackups  `json:"velero"`
	Postgresql PostgresBackups `json:"postgresql"`
	PolicyGaps []PolicyGap    `json:"policyGaps"`
}

// ---- /database ---------------------------------------------------------------------

type HistoricalQualification struct {
	Scope           string `json:"scope"`
	Date            string `json:"date"`
	LatestRestore   string `json:"latestRestore"`
	Pitr            string `json:"pitr"`
	IsLiveRecoveryTest bool `json:"isLiveRecoveryTest"`
}

type Database struct {
	Namespace                string                  `json:"namespace"`
	Cluster                  string                  `json:"cluster"`
	Health                   string                  `json:"health"`
	DesiredInstances         *int32                  `json:"desiredInstances"`
	ReadyInstances           *int32                  `json:"readyInstances"`
	PrimaryName              *string                 `json:"primaryName"`
	ReplicasObserved         *int32                  `json:"replicasObserved"`
	ReplicasInferred         bool                    `json:"replicasInferred"`
	Phase                    *string                 `json:"phase"`
	Conditions               []Condition             `json:"conditions"`
	ApplicationDbConnected   bool                    `json:"applicationDbConnected"`
	RecoveryState            *string                 `json:"recoveryState"`
	HistoricalQualification  HistoricalQualification `json:"historicalQualification"`
}

// ---- /metrics ----------------------------------------------------------------------

type Metric struct {
	Kind                        string   `json:"kind"` // Node|Pod
	Name                        string   `json:"name"`
	Namespace                   *string  `json:"namespace"`
	SampleTimestamp             string   `json:"sampleTimestamp"`
	WindowSeconds               float64  `json:"windowSeconds"`
	CpuCores                    *float64 `json:"cpuCores"`
	MemoryBytes                 *int64   `json:"memoryBytes"`
	CpuPercentOfAllocatable     *float64 `json:"cpuPercentOfAllocatable"`
	MemoryPercentOfAllocatable  *float64 `json:"memoryPercentOfAllocatable"`
}

// ---- /events ------------------------------------------------------------------------

type TimelineEvent struct {
	ID              string  `json:"id"`
	Source          string  `json:"source"` // kubernetes|portal-status
	SourceTime      *string `json:"sourceTime"`
	IngestedAt      string  `json:"ingestedAt"`
	Severity        string  `json:"severity"`
	ObjectKind      *string `json:"objectKind"`
	Namespace       *string `json:"namespace"`
	ObjectName      *string `json:"objectName"`
	ReasonCode      string  `json:"reasonCode"`
	OccurrenceCount int64   `json:"occurrenceCount"`
	Message         string  `json:"message"`
}

type Events struct {
	Storage       string          `json:"storage"` // postgresql|memory-fallback
	AuditComplete bool            `json:"auditComplete"` // always false in P8C
	Items         []TimelineEvent `json:"items"`
}

// ---- list wrappers ----------------------------------------------------------------

type Nodes struct     { Items []Node `json:"items"` }
type Workloads struct { Items []Workload `json:"items"` }
type Pods struct     { Items []Pod `json:"items"` }
type Services struct  { Items []Service `json:"items"` }
type Metrics struct   { Items []Metric `json:"items"` }

// ---- error --------------------------------------------------------------------------

type Error struct {
	RequestID   string `json:"requestId"`
	GeneratedAt string `json:"generatedAt"`
	Code        string `json:"code"` // BAD_REQUEST|CURSOR_EXPIRED|UNAUTHORIZED|NOT_FOUND|METHOD_NOT_ALLOWED|RATE_LIMITED|UNAVAILABLE
	Message     string `json:"message"`
}
