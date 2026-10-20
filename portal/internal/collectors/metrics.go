package collectors

import (
	"context"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// allowedMetricNames are the exactly three permitted Barman metric families
// (P8B-R2 verified on CNPG instance metrics endpoint).
var allowedMetricNames = []string{
	"barman_cloud_cloudnative_pg_io_first_recoverability_point",
	"barman_cloud_cloudnative_pg_io_last_available_backup_timestamp",
	"barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp",
}

// collectBarmanMetrics fetches the three allowed metric families from the
// dedicated ClusterIP metrics service. No redirects, 5s timeout, 1 MiB cap.
// Metrics are optional supporting evidence: on failure the source is visible
// as unavailable, not a fatal error.
func (c *Collector) collectBarmanMetrics(ctx context.Context, snap *Snapshot) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.metricsURL, nil)
	if err != nil {
		snap.addWarning("barman-metrics: request error")
		return
	}
	client := &http.Client{
		Timeout: 5 * time.Second,
		CheckRedirect: func(*http.Request, []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}
	resp, err := client.Do(req)
	if err != nil {
		snap.addWarning("barman-metrics: unavailable")
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		snap.addWarning("barman-metrics: status " + resp.Status)
		return
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		snap.addWarning("barman-metrics: read error")
		return
	}
	parsePrometheusMetrics(string(body), snap.BarmanMetrics)
	ts := time.Now().UTC().Format(time.RFC3339)
	age := int64(0)
	snap.addSource(model.SourceStatus{ID: "barman-metrics", State: "fresh", ObservedAt: &ts, AgeSeconds: &age})
}

// parsePrometheusMetrics extracts the allowed metric values (latest sample wins).
func parsePrometheusMetrics(text string, out map[string]string) {
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// name{labels} value  OR  name value
		idx := strings.IndexAny(line, " {")
		if idx < 0 {
			continue
		}
		name := line[:idx]
		if !isAllowedMetric(name) {
			continue
		}
		value := metricValue(line)
		out[name] = value
	}
}

func isAllowedMetric(name string) bool {
	for _, n := range allowedMetricNames {
		if name == n {
			return true
		}
	}
	return false
}

// metricValue returns the numeric value after the last whitespace token.
func metricValue(line string) string {
	fields := strings.Fields(line)
	if len(fields) < 2 {
		return ""
	}
	return fields[len(fields)-1]
}
