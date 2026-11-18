"""Remaining R1: terminate actual I/O; consume every applicable counter before return.
Run from repository root. No IP connections: real HTTPResponse on anonymous AF_UNIX only.
"""
import http.client
import json
import pathlib
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path.cwd() / 'portal/tools/readiness'))
import wrapper as w


class TerminalLifecycle(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = patch.object(w, 'RESERVATION_BASE', str(pathlib.Path(tmp.name) / 'authority'))
        p.start()
        self.addCleanup(p.stop)
        self.g = {'package_sha256': 'd' * 64}
        w._reset_transport()
        w._reset_read_cache()
        w._set_budget_base({})
        w._set_budget_context(self.g, None, {})
        self.addCleanup(w._set_budget_context, None, None, None)
        self.addCleanup(w._reset_transport)

    def test_headers_io_terminated_before_terminal_return(self):
        left, right = socket.socketpair()
        stopped = threading.Event()
        open_entered = threading.Event()
        open_finished = threading.Event()
        progress = []
        workers = []

        def writer():
            try:
                right.sendall(b'HTTP/1.1 200 OK\r\nX-Test: ')
                for _ in range(100):
                    if stopped.wait(.01):
                        return
                    right.sendall(b'x')
                    progress.append(time.monotonic())
                right.sendall(b'\r\nContent-Length: 0\r\n\r\n')
            except OSError:
                pass

        class Opener:
            def open(self, *args, **kwargs):
                workers.append(threading.current_thread())
                left.settimeout(kwargs['timeout'])
                response = http.client.HTTPResponse(left)
                open_entered.set()
                try:
                    response.begin()
                except BaseException:
                    response.close()
                    raise
                finally:
                    open_finished.set()
                return response

        producer = threading.Thread(target=writer, daemon=True)
        producer.start()
        try:
            with patch('urllib.request.build_opener', return_value=Opener()):
                started = time.monotonic()
                with self.assertRaises(w.ReadError):
                    w._io_call(w.default_http_get, 'http://127.0.0.1:9187/metrics', .05, 1024)
                returned = time.monotonic()
                self.assertTrue(open_entered.is_set())
                self.assertLessEqual(returned - started, .11)
                # Brief observation only: successful cancellation must have ended begin() already.
                finished_at_return = open_finished.is_set()
                time.sleep(.06)
                after = sum(t > returned for t in progress)
                self.assertTrue(finished_at_return and open_finished.is_set(),
                                {'open_finished_at_return': finished_at_return,
                                 'open_finished_after_60ms': open_finished.is_set(),
                                 'bytes_sent_after_return': after,
                                 'worker_alive': any(t.is_alive() for t in workers)})
        finally:
            stopped.set()
            for s in (left, right):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            left.close()
            right.close()
            producer.join(1)
            for worker in workers:
                worker.join(1)

    def metadata_charge(self, concurrent=False):
        body = json.dumps({'kind': 'Cluster', 'apiVersion': 'postgresql.cnpg.io/v1',
                           'metadata': {'uid': 'c'}, 'status': {}}).encode()
        calls = []

        def transport(kubectl, path, timeout, cap):
            calls.append(cap)
            self.assertGreaterEqual(cap, len(body))
            if concurrent:
                # Another completed I/O consumes remaining overall bytes while this one is in flight.
                w._charge(self.g, 'bytes', w.OVERALL_BODY_CAP - 1, w.OVERALL_BODY_CAP)
            return body, 0

        with patch.object(w, 'run_kubectl_raw', side_effect=transport):
            result = w.run_wal_sample('FAKE', None, None, self.g)
        return result, w.read_budget(self.g), len(body), calls

    def test_metadata_body_charges_wal_even_when_overall_charge_overruns(self):
        result, budget, size, calls = self.metadata_charge(concurrent=True)
        self.assertEqual(result[0], w.INCONCLUSIVE)
        self.assertEqual(len(calls), 1)
        self.assertEqual(budget['bytes'], w.OVERALL_BODY_CAP - 1 + size)
        self.assertEqual(budget['wal_bytes'], size, budget)

    def test_metadata_body_normal_charge_positive(self):
        result, budget, size, calls = self.metadata_charge()
        self.assertEqual(result[0], w.INCONCLUSIVE)  # No currentPrimary; consumption still required.
        self.assertEqual(len(calls), 1)
        self.assertEqual((budget['bytes'], budget['wal_bytes']), (size, size))


if __name__ == '__main__':
    unittest.main(verbosity=2)
