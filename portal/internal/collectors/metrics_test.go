package collectors

import "testing"

func TestParsePrometheusMetrics(t *testing.T) {
	text := `# HELP barman_cloud_cloudnative_pg_io_first_recoverability_point The first point
# TYPE barman_cloud_cloudnative_pg_io_first_recoverability_point gauge
barman_cloud_cloudnative_pg_io_first_recoverability_point 1.79246971e+09
barman_cloud_cloudnative_pg_io_last_available_backup_timestamp 1.79246971e+09
barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp 0
cnpg_cache_hits 2
`
	out := map[string]string{}
	parsePrometheusMetrics(text, out)
	if got := out["barman_cloud_cloudnative_pg_io_first_recoverability_point"]; got != "1.79246971e+09" {
		t.Fatalf("first_recoverability_point = %q, want 1.79246971e+09", got)
	}
	if got := out["barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp"]; got != "0" {
		t.Fatalf("last_failed = %q, want 0", got)
	}
	if _, ok := out["cnpg_cache_hits"]; ok {
		t.Fatal("non-allowed metric must not be captured")
	}
}

func TestMetricValueWithLabels(t *testing.T) {
	if got := metricValue("barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp{instance=\"x\"} 0"); got != "0" {
		t.Fatalf("metricValue = %q, want 0", got)
	}
}
