"""Explicit direct or loopback HTTP CONNECT transport; never auto-detect/fallback.

Configuration is local-only. The sole certificate probe occurs at the already
authorized launch boundary, with the same transport Chromium receives.
"""
import re
import socket
import ssl
import time

from .core import ORIGIN, APPROVED_CERT_DER, APPROVED_SPKI, require, sha, write_new, record_exception


def validate_transport(value):
    require(type(value) is dict and set(value) == {"mode", "proxy_server"}, "EXPLICIT_TRANSPORT_REQUIRED")
    if value["mode"] == "DIRECT":
        require(value["proxy_server"] is None, "DIRECT_HAS_NO_PROXY")
        return None
    require(value["mode"] == "HTTP_CONNECT_PROXY" and type(value["proxy_server"]) is str,
            "TRANSPORT_MODE_NOT_SUPPORTED")
    match = re.fullmatch(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", value["proxy_server"])
    require(match is not None and int(match[1]) <= 65535, "CREDENTIALLESS_LOOPBACK_HTTP_PROXY_REQUIRED")
    return ("127.0.0.1", int(match[1]))


def launch_arguments(binding):
    transport, setting = binding.data["transport"], binding.data["tls"]
    proxy = validate_transport(transport)
    args = (["--no-proxy-server"] if proxy is None else
            ["--proxy-server=" + transport["proxy_server"], "--proxy-bypass-list=<-loopback>"])
    if setting["mode"] == "STRICT":
        return args
    require(setting["mode"] == "USER_APPROVED_EXACT_CERT" and setting["origin"] == ORIGIN and
            setting["leaf_der_sha256"] == APPROVED_CERT_DER and setting["spki_sha256_base64"] == APPROVED_SPKI,
            "EXACT_CERT_AND_ORIGIN_REQUIRED")
    evidence = {"schema": "UsenseBoundTLSProbe/v1", "transport": transport, "origin": ORIGIN,
                "phase": "CONNECT", "attempts": 1, "fallback_allowed": False,
                "proxy_connect_sent": False, "leaf_sha256": None, "status": "STARTED"}
    deadline = time.monotonic() + 10

    def remaining(sock):
        seconds = deadline - time.monotonic()
        require(seconds > 0, "TLS_PROBE_DEADLINE")
        sock.settimeout(seconds)

    try:
        # No environment, WinINET, WinHTTP, PAC, credentials or alternate proxy.
        with socket.create_connection(proxy or ("www.usense.com", 443), timeout=10) as sock:
            if proxy is not None:
                evidence["phase"] = "PROXY_CONNECT"
                remaining(sock)
                request = b"CONNECT www.usense.com:443 HTTP/1.1\r\nHost: www.usense.com:443\r\n\r\n"
                with (binding.output / "proxy-connect-request.raw").open("xb") as stream:
                    stream.write(request)
                sock.sendall(request)
                evidence["proxy_connect_sent"] = True
                header = bytearray()
                # Read exactly through the header, never consume TLS bytes.
                while not header.endswith(b"\r\n\r\n"):
                    require(len(header) < 8192, "PROXY_CONNECT_HEADER_TOO_LARGE")
                    remaining(sock)
                    part = sock.recv(1)
                    require(bool(part), "PROXY_CONNECT_EOF")
                    header.extend(part)
                first = bytes(header).split(b"\r\n", 1)[0]
                evidence["proxy_response_sha256"] = sha(bytes(header))
                with (binding.output / "proxy-connect-response.raw").open("xb") as stream:
                    stream.write(header)
                require(re.fullmatch(rb"HTTP/1\.[01] 200(?: [^\r\n]*)?", first) is not None,
                        "PROXY_CONNECT_NOT_200_NO_FALLBACK")
            evidence["phase"] = "TLS_HANDSHAKE"
            remaining(sock)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # Eligibility is the exact DER below, then the original SPKI in Chromium.
            with context.wrap_socket(sock, server_hostname="www.usense.com") as secure:
                cert = secure.getpeercert(binary_form=True)
            evidence["phase"] = "LEAF_CERTIFICATE_CHECK"
            evidence["leaf_sha256"] = sha(cert)
            require(evidence["leaf_sha256"] == setting["leaf_der_sha256"], "APPROVED_CERTIFICATE_CHANGED")
        evidence.update(phase="READY_TO_LAUNCH", status="EXACT_LEAF_CONFIRMED")
    except BaseException as exc:
        evidence["status"] = "FAILED_NO_RETRY"
        evidence["error"] = record_exception(binding.output, "tls-probe-error", exc, evidence["phase"])
        raise
    finally:
        write_new(binding.output / "tls-probe.json", evidence)
    return args + ["--ignore-certificate-errors-spki-list=" + setting["spki_sha256_base64"]]
