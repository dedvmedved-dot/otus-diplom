package collectors

import (
	"context"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// allowedMetricNames are the exactly three permitted Barman metric families.
var allowedMetricNames = []string{
	"barman_cloud_cloudnative_pg_io_first_recoverability_point",
	"barman_cloud_cloudnative_pg_io_last_available_backup_timestamp",
	"barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp",
}

// collectBarmanMetrics fetches the three allowed metric families from the
// dedicated ClusterIP metrics service. No redirects, 5s timeout, 1 MiB cap.
// Metrics are supporting evidence: on failure the source is visible as error.
func (c *Collector) collectBarmanMetrics(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.metricsURL, nil)
	if err != nil {
		snap.setPartial()
		reg.set(sourceStatus("barman/metrics", "error", now, err))
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
		snap.setPartial()
		reg.set(sourceStatus("barman/metrics", "error", now, err))
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		snap.setPartial()
		reg.set(sourceStatus("barman/metrics", "error", now, errBadStatus(resp.StatusCode)))
		return
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		snap.setPartial()
		reg.set(sourceStatus("barman/metrics", "error", now, err))
		return
	}
	vals := map[string]string{}
	parsePrometheusMetrics(string(body), vals)
	if len(vals) == 0 {
		snap.setPartial()
		reg.set(sourceStatus("barman/metrics", "error", now, errNoMetrics()))
		return
	}
	reg.set(sourceStatus("barman/metrics", "ok", now, nil))
	sample := barmanSampleFrom(vals, now)
	snap.mu.Lock()
	snap.Barman = &sample
	snap.mu.Unlock()
}

// Snapshot.Barman holds the parsed single-exporter sample (added field).
// Kept out of model to avoid import cycle; it is a model.BarmanSample.

func barmanSampleFrom(vals map[string]string, now time.Time) model.BarmanSample {
	sampled := now.UTC().Format(time.RFC3339)
	return model.BarmanSample{
		SampledAt:                         &sampled,
		Scope:                             "single_exporter_sample",
		LastAvailableBackupTimestamp:      parseFloatMetric(vals["barman_cloud_cloudnative_pg_io_last_available_backup_timestamp"]),
		FirstRecoverabilityPointTimestamp: parseFloatMetric(vals["barman_cloud_cloudnative_pg_io_first_recoverability_point"]),
		LastFailedBackupTimestamp:         parseFloatMetric(vals["barman_cloud_cloudnative_pg_io_last_failed_backup_timestamp"]),
	}
}

func parseFloatMetric(s string) *float64 {
	if s == "" || s == "NaN" || s == "+Inf" || s == "-Inf" {
		return nil
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return nil
	}
	return &f
}

func errBadStatus(code int) error { return &httpError{code: code} }

type httpError struct{ code int }

func (e *httpError) Error() string { return "metrics http " + itoa(e.code) }

func errNoMetrics() error { return &noMetricsError{} }

type noMetricsError struct{}

func (noMetricsError) Error() string { return "no allowed barman metrics present" }

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b [20]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}

// parsePrometheusMetrics extracts the allowed metric values (latest sample wins).
func parsePrometheusMetrics(text string, out map[string]string) {
	for _, line := range strings.Split(text, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		idx := strings.IndexAny(line, " {")
		if idx < 0 {
			continue
		}
		name := line[:idx]
		if !isAllowedMetric(name) {
			continue
		}
		out[name] = metricValue(line)
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

func metricValue(line string) string {
	fields := strings.Fields(line)
	if len(fields) < 2 {
		return ""
	}
	return fields[len(fields)-1]
}
