SOURCE_TEST_GATE = PASS
go test ./weed/s3api/s3_objectlock/ ./weed/s3api/s3lifecycle/... ./weed/s3api/policy_engine/ ./weed/s3api/s3bucket/ -count=1
RESULT: TEST_EXIT=0; all packages 'ok' (objectlock 0.115s, lifecycle* ok, policy_engine ok, s3bucket ok).
