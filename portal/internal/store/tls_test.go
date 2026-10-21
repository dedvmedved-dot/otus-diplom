package store

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"math/big"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func tlsFixture(t *testing.T) (*config.Config, tls.Certificate) {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	cert := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: config.DBHost}, DNSNames: []string{config.DBHost}, NotBefore: time.Now().Add(-time.Hour), NotAfter: time.Now().Add(time.Hour), IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth}}
	der, err := x509.CreateCertificate(rand.Reader, cert, cert, &key.PublicKey, key)
	if err != nil {
		t.Fatal(err)
	}
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der})
	pair, err := tls.X509KeyPair(certPEM, pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)}))
	if err != nil {
		t.Fatal(err)
	}
	ca := filepath.Join(t.TempDir(), "public-ca.crt")
	if err := os.WriteFile(ca, certPEM, 0600); err != nil {
		t.Fatal(err)
	}
	return &config.Config{DBCACertFile: ca, DBPassword: "synthetic-only", DBPoolMaxConns: 5, DBConnectTimeout: time.Second}, pair
}
func TestFixedTLSConfigAndHandshake(t *testing.T) {
	cfg, cert := tlsFixture(t)
	pc, err := poolConfig(cfg)
	if err != nil {
		t.Fatal(err)
	}
	cc := pc.ConnConfig
	if cc.Host != config.DBHost || cc.Port != 5432 || cc.User != "portal_app" || cc.Database != "portal" || cc.Password != cfg.DBPassword || len(cc.Fallbacks) != 0 || cc.TLSConfig.MinVersion != tls.VersionTLS12 || cc.TLSConfig.ServerName != config.DBHost || cc.TLSConfig.InsecureSkipVerify {
		t.Fatal("DB contract violated")
	}
	if len(cc.RuntimeParams) != 2 || cc.RuntimeParams["search_path"] != "portal,pg_catalog" {
		t.Fatal("ambient runtime params")
	}
	server := httptest.NewUnstartedServer(nil)
	server.TLS = &tls.Config{Certificates: []tls.Certificate{cert}, MinVersion: tls.VersionTLS12}
	server.StartTLS()
	defer server.Close()
	addr := strings.TrimPrefix(server.URL, "https://")
	conn, err := tls.Dial("tcp", addr, cc.TLSConfig)
	if err != nil {
		t.Fatal(err)
	}
	conn.Close()
	wrongName := cc.TLSConfig.Clone()
	wrongName.ServerName = "wrong.invalid"
	if conn, err := tls.Dial("tcp", addr, wrongName); err == nil {
		conn.Close()
		t.Fatal("wrong hostname accepted")
	}
	wrongCA := cc.TLSConfig.Clone()
	wrongCA.RootCAs = x509.NewCertPool()
	if conn, err := tls.Dial("tcp", addr, wrongCA); err == nil {
		conn.Close()
		t.Fatal("untrusted CA accepted")
	}
}
func TestAllAmbientPGOverridesRejectedBeforeParsing(t *testing.T) {
	keys := []string{"PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGPASSFILE", "PGAPPNAME", "PGCONNECT_TIMEOUT", "PGSSLMODE", "PGSSLKEY", "PGSSLCERT", "PGSSLSNI", "PGSSLROOTCERT", "PGSSLPASSWORD", "PGSSLNEGOTIATION", "PGTARGETSESSIONATTRS", "PGSERVICE", "PGSERVICEFILE", "PGTZ", "PGOPTIONS", "PGMINPROTOCOLVERSION", "PGMAXPROTOCOLVERSION", "PGCHANNELBINDING", "PGREQUIREAUTH"}
	for _, key := range keys {
		t.Run(key, func(t *testing.T) {
			t.Setenv(key, "synthetic-override")
			_, err := poolConfig(&config.Config{DBCACertFile: "/missing"})
			if err == nil || err.Error() != "ambient PG configuration forbidden" {
				t.Fatalf("did not reject %s before reading files", key)
			}
			if strings.Contains(err.Error(), "synthetic-override") {
				t.Fatal("credential-bearing error")
			}
		})
	}
}
