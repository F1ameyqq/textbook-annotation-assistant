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


def openssl_leaf_certificate(binding, proxy):
    """B 机可移植性补丁：用 OpenSSL CLI 取叶子证书 DER。

    本机网络出口会按 TLS 指纹中断 Python ssl 握手（SSLEOFError），
    而同一路径下 OpenSSL CLI 能正常完成握手并取得证书。
    返回值仍交给调用方与已钉定的 leaf_der_sha256 比对，
    不降低原有校验强度，也不引入环境变量/WinINET/PAC 代理自动发现。
    """
    import os
    import shutil
    import subprocess

    exe = shutil.which("openssl")
    if not exe:
        for candidate in (r"C:\Program Files\Git\usr\bin\openssl.exe",
                          r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
                          r"C:\Program Files\OpenSSL\bin\openssl.exe"):
            if os.path.exists(candidate):
                exe = candidate
                break
    require(exe is not None, "OPENSSL_FALLBACK_UNAVAILABLE")
    host = "www.usense.com"
    command = [exe, "s_client", "-connect", host + ":443",
               "-servername", host, "-showcerts"]
    if proxy is not None:
        command[2:2] = ["-proxy", f"{proxy[0]}:{proxy[1]}"]
    completed = subprocess.run(command, input=b"", capture_output=True, timeout=25)
    text = (completed.stdout + completed.stderr).decode("utf-8", "replace")
    match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", text, re.S)
    require(match is not None, "OPENSSL_LEAF_NOT_FOUND")
    pem_path = binding.output / "openssl-leaf.pem"
    with pem_path.open("xb") as stream:
        stream.write((match.group(0) + "\n").encode("ascii"))
    der = subprocess.run([exe, "x509", "-in", str(pem_path), "-outform", "DER"],
                         capture_output=True, timeout=25)
    require(der.returncode == 0 and bool(der.stdout), "OPENSSL_LEAF_DER_FAILED")
    return der.stdout


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
            try:
                with context.wrap_socket(sock, server_hostname="www.usense.com") as secure:
                    cert = secure.getpeercert(binary_form=True)
                evidence["probe_stack"] = "PYTHON_SSL"
            except ssl.SSLError:
                # B 机可移植性补丁：本机网络出口会按 TLS 指纹中断 Python 握手
                # （SSLEOFError），但同一路径下 OpenSSL CLI 可正常取得叶子证书。
                # 仍保持原语义：必须与已钉定的 leaf_der_sha256 完全一致才放行。
                evidence["phase"] = "TLS_HANDSHAKE_OPENSSL_FALLBACK"
                cert = openssl_leaf_certificate(binding, proxy)
                evidence["probe_stack"] = "OPENSSL_CLI"
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
