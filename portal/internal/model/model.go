// Package model defines the sanitized DTO types returned by the Portal API.
// No raw Kubernetes object (spec.env, commands, volumes, annotations, secret
// refs) is ever serialized into these types.
package model

import "time"

// SourceStatus describes the collection state of one data source.
type SourceStatus struct {
	ID          string  `json:"id"`
	State       string  `json:"state"` // fresh|stale|error|unsupported|partial
	ObservedAt  *string `json:"observedAt"`
	AgeSeconds  *int64  `json:"ageSeconds"`
	ErrorCode   *string `json:"errorCode"`
}

// Envelope is the common response wrapper for all list endpoints.
type Envelope struct {
	RequestID   string         `json:"requestId"`
	GeneratedAt string         `json:"generatedAt"`
	ObservedAt  *string        `json:"observedAt"`
	Freshness   string         `json:"freshness"`
	Partial     bool           `json:"partial"`
	Sources     []SourceStatus `json:"sources"`
	Data        any            `json:"data"`
	Warnings    []string       `json:"warnings"`
	NextCursor  *string        `json:"nextCursor"`
}

// NodeInfo is the sanitized node projection.
type NodeInfo struct {
	Name          string            `json:"name"`
	Ready         bool              `json:"ready"`
	Roles         []string          `json:"roles"`
	Version       string            `json:"version"`
	Conditions    map[string]string `json:"conditions"` // only condition type -> status
	CPUCapacity   string            `json:"cpuCapacity"`
	MemoryCapacity string           `json:"memoryCapacity"`
	CPUAllocatable string           `json:"cpuAllocatable"`
	MemoryAllocatable string        `json:"memoryAllocatable"`
}

// WorkloadInfo aggregates Deployment/StatefulSet/DaemonSet/ReplicaSet/Job/CronJob.
type WorkloadInfo struct {
	Kind        string `json:"kind"`
	Namespace   string `json:"namespace"`
	Name        string `json:"name"`
	Ready       string `json:"ready"`
	Desired     int32  `json:"desired"`
	Current     int32  `json:"current"`
	UpToDate    int32  `json:"upToDate"`
	Available   int32  `json:"available"`
	Suspended   bool   `json:"suspended,omitempty"`
}

// PodInfo is the sanitized pod projection (no spec/env/logs).
type PodInfo struct {
	Namespace  string `json:"namespace"`
	Name       string `json:"name"`
	Phase      string `json:"phase"`
	Ready      string `json:"ready"`
	Restarts   int32  `json:"restarts"`
	NodeName   string `json:"nodeName"`
}

// ServiceInfo is the sanitized service projection (no generic proxy).
type ServiceInfo struct {
	Namespace string   `json:"namespace"`
	Name      string   `json:"name"`
	Type      string   `json:"type"`
	Ports     []string `json:"ports"`
	Endpoints int      `json:"endpoints"`
}

// StorageInfo aggregates PVC/PV/StorageClass/VolumeSnapshot.
type StorageInfo struct {
	Kind        string `json:"kind"`
	Namespace   string `json:"namespace"`
	Name        string `json:"name"`
	Phase       string `json:"phase"`
	Capacity    string `json:"capacity"`
	StorageClass string `json:"storageClass"`
	BoundTo     string `json:"boundTo,omitempty"`
}

// BackupInfo aggregates Velero and CNPG/Barman backup observations.
type BackupInfo struct {
	Domain      string `json:"domain"` // velero|postgresql
	Kind        string `json:"kind"`
	Namespace   string `json:"namespace"`
	Name        string `json:"name"`
	Phase       string `json:"phase"`
	Available   bool   `json:"available,omitempty"`
	StartedAt   string `json:"startedAt,omitempty"`
	ExpiresAt   string `json:"expiresAt,omitempty"`
}

// DatabaseInfo is the CNPG cluster projection.
type DatabaseInfo struct {
	Name          string `json:"name"`
	Desired       int32  `json:"desired"`
	Ready         int32  `json:"ready"`
	CurrentPrimary string `json:"currentPrimary"`
	Phase         string `json:"phase"`
	Replicas      int32  `json:"replicas"`
	ReplicaInferred bool `json:"replicaInferred"`
	LastFullBackupAge string `json:"lastFullBackupAge,omitempty"`
	WALArchiving  string `json:"walArchiving"`
}

// MetricInfo is a single metrics-sample projection (cores/bytes).
type MetricInfo struct {
	Kind      string `json:"kind"` // node|pod
	Namespace string `json:"namespace,omitempty"`
	Name      string `json:"name"`
	CPU       string `json:"cpu"`
	Memory    string `json:"memory"`
	Window    string `json:"window"`
}

// EventInfo is the sanitized timeline event.
type EventInfo struct {
	IngestedAt  string  `json:"ingestedAt"`
	SourceTime  *string `json:"sourceTime"`
	Source      string  `json:"source"`
	Severity    string  `json:"severity"`
	ObjectKind  string  `json:"objectKind"`
	ObjectNS    string  `json:"objectNamespace"`
	ObjectName  string  `json:"objectName"`
	ReasonCode  string  `json:"reasonCode"`
	Occurrences int64   `json:"occurrenceCount"`
	Message     string  `json:"message"`
}

// HealthInfo is the /health response data.
type HealthInfo struct {
	Process         string `json:"process"`
	DBConnectivity  string `json:"dbConnectivity"`
	SchemaVersion   string `json:"schemaVersion"`
	Collector       string `json:"collector"`
	Build           string `json:"build"`
}

// SummaryInfo is the /summary response data.
type SummaryInfo struct {
	OverallHealth string            `json:"overallHealth"`
	Counts        map[string]int    `json:"counts"`
	Alerts        []string          `json:"alerts"`
	PolicyGaps    []string          `json:"policyGaps"`
	ObservedAt    *time.Time        `json:"observedAt,omitempty"`
}
