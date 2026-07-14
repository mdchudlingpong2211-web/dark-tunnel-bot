"""Core Dark Tunnel `.dark` config parsing, decryption, and re-encoding logic.

This module intentionally mirrors the original bot's decrypt/unlock behaviour
exactly -- only structure, naming, typing, and error handling were improved.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

from app.config import INNER_KEY, OUTER_KEY
from app.crypto_utils import aes_cfb_decrypt, b64decode_any
from app.msgpack_reader import msgpack_unpack

logger = logging.getLogger(__name__)


def parse_dark_content(text: str) -> dict[str, Any]:
    """Parse either a raw JSON `.dark` export or a `darktunnel://` URI."""
    text = text.strip()
    if "darktunnel://" in text:
        text = text.split("darktunnel://", 1)[1].split()[0]
        return json.loads(b64decode_any(text))
    return json.loads(text)


def maybe_parse_text(text: str) -> Any:
    stripped = text.strip()
    if stripped[:1] in ("{", "["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    return text


def bytes_for_json(value: bytes) -> Any:
    if len(value) == 96:
        head, tail = value[:64], value[64:]
        try:
            head_text = head.decode("ascii")
            if all(ch in "0123456789abcdefABCDEF" for ch in head_text):
                return {
                    "hash_hex": head_text,
                    "extra_hash_hex": tail.hex(),
                    "length": len(value),
                }
        except UnicodeDecodeError:
            pass
    try:
        return maybe_parse_text(value.decode("utf-8"))
    except UnicodeDecodeError:
        return {
            "bytes_b64": base64.b64encode(value).decode("ascii"),
            "bytes_hex": value.hex(),
            "length": len(value),
        }


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(json_safe(k)): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, bytes):
        return bytes_for_json(value)
    return value


def decrypt_value(value: bytes) -> Any:
    if not value:
        return ""
    return bytes_for_json(aes_cfb_decrypt(value, INNER_KEY))


def decrypt_inner_fields(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            if key_text.startswith("Encrypted") and isinstance(item, bytes):
                clean_key = key_text[len("Encrypted") :]
                out[clean_key] = decrypt_value(item)
            else:
                out[key_text] = decrypt_inner_fields(item)
        return out
    if isinstance(value, list):
        return [decrypt_inner_fields(item) for item in value]
    if isinstance(value, bytes):
        return bytes_for_json(value)
    return value


_CAMEL_CASE_OVERRIDES = {
    "V2RayConfig": "v2rayConfig",
    "SshConfig": "sshConfig",
    "InjectConfig": "injectConfig",
    "DnsttDnsHost": "dnsttUdpDnsHost",
    "DnsttDnsPort": "dnsttUdpDnsPort",
    "DnsttPubkey": "dnsttPublicKey",
}


def to_camel_case(d: Any) -> Any:
    if isinstance(d, dict):
        new_d: dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(k, str) and k:
                new_k = _CAMEL_CASE_OVERRIDES.get(k, k[0].lower() + k[1:])
                new_d[new_k] = to_camel_case(v)
            else:
                new_d[k] = to_camel_case(v)
        return new_d
    if isinstance(d, list):
        return [to_camel_case(i) for i in d]
    return d


def _apply_v2ray_config(v: dict[str, Any], tunnel_type: str, tunnel_config: dict[str, Any]) -> None:
    """Populate host/port/uuid/etc. from an embedded v2ray config blob."""
    if "config" not in v:
        return

    if tunnel_type == "V2RAY_CUSTOM_CONFIG":
        raw = v.pop("config")
        tunnel_config["v2rayCustomConfig"] = json.dumps(raw) if isinstance(raw, dict) else str(raw)
        v.pop("isInjectModeEnabled", None)
        return

    try:
        raw_config = v["config"]
        if isinstance(raw_config, str):
            safe_json = re.sub(r":\s*\$[A-Z0-9_]+", ": true", raw_config)
            v2_data = json.loads(safe_json)
        else:
            v2_data = raw_config

        outbounds = v2_data.get("outbounds", [])
        if outbounds:
            ob = outbounds[0]
            settings = ob.get("settings", {})
            stream = ob.get("streamSettings", {})
            vnext = settings.get("vnext", [{}])[0]
            users = vnext.get("users", [{}])[0]
            if not vnext and settings.get("servers"):
                vnext = settings.get("servers", [{}])[0]
                users = vnext

            v["host"] = vnext.get("address", "")
            v["port"] = vnext.get("port", 443)
            v["uuid"] = users.get("id", "") or users.get("password", "")
            v["serverNameIndication"] = stream.get("tlsSettings", {}).get("serverName", "")

            net = stream.get("network", "")
            if net == "ws":
                v["wsPath"] = stream.get("wsSettings", {}).get("path", "")
                v["wsHeaderHost"] = stream.get("wsSettings", {}).get("headers", {}).get("Host", "")
            elif net == "grpc":
                v["grpcServiceName"] = stream.get("grpcSettings", {}).get("serviceName", "")
    except (json.JSONDecodeError, AttributeError, IndexError, TypeError) as exc:
        logger.debug("Could not fully parse embedded v2ray config: %s", exc)
    finally:
        v.pop("config", None)
        v.pop("isInjectModeEnabled", None)


def create_unlocked_config(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Transform a decrypted Dark Tunnel config into its "unlocked" shape."""
    unlocked = json.loads(json.dumps(config_dict))
    decrypted_locked = unlocked.pop("decryptedLockedConfig", {})
    inner_config = decrypted_locked.get("DecryptedInnerConfig")

    if not inner_config:
        return unlocked

    camel_inner = to_camel_case(inner_config)
    tunnel_type = unlocked.get("type", "")
    parts = tunnel_type.lower().split("_")
    tunnel_config_key = parts[0] + "".join(p.capitalize() for p in parts[1:]) + "TunnelConfig"

    tunnel_config = unlocked.setdefault(tunnel_config_key, {})

    for k, v in camel_inner.items():
        if not isinstance(v, dict):
            continue

        v.pop("isEncrypted", None)
        v.pop("isLocked", None)

        if k == "v2rayConfig":
            _apply_v2ray_config(v, tunnel_type, tunnel_config)

        for int_key in ("port", "proxyPort", "dnsttUdpDnsPort"):
            if int_key in v:
                try:
                    v[int_key] = int(v[int_key])
                except (TypeError, ValueError):
                    pass

        if k in tunnel_config and isinstance(tunnel_config[k], dict):
            tunnel_config[k].update(v)
        else:
            tunnel_config[k] = v

    if tunnel_type == "SSH_DNSTT":
        inj = tunnel_config.pop("injectConfig", {})
        if inj:
            dnstt_config = {
                "udpDnsHost": inj.get("dnsttUdpDnsHost", ""),
                "serverName": inj.get("dnsttServerName", ""),
                "publicKey": inj.get("dnsttPublicKey", ""),
            }
            port = inj.get("dnsttUdpDnsPort")
            if port and port not in (53, "53"):
                dnstt_config["udpDnsPort"] = int(port)
            tunnel_config["dnsttConfig"] = dnstt_config

    for k in list(tunnel_config.keys()):
        val = tunnel_config[k]
        if not isinstance(val, dict):
            continue
        for sub_k in [sub_k for sub_k, sub_v in val.items() if sub_v == "" and sub_k != "payload"]:
            del val[sub_k]
        if not val:
            del tunnel_config[k]
        elif k == "sshConfig" and not val.get("host") and not val.get("username"):
            del tunnel_config[k]
        elif (
            k == "injectConfig"
            and not val.get("proxyHost")
            and "payload" not in val
            and not val.get("dnsttServerName")
        ):
            del tunnel_config[k]
        elif k == "v2rayConfig" and not val.get("host") and not val.get("uuid"):
            del tunnel_config[k]

    return unlocked


def process_dark_config(content: str) -> dict[str, Any]:
    """Parse and decrypt a raw `.dark` export into a plain dict.

    Raises `DarkConfigError` (safe to show to end users) on any parse/decrypt
    failure; the original exception is chained for server-side log detail.
    """
    try:
        config = parse_dark_content(content)
        encrypted = config.pop("encryptedLockedConfig", None)
        if not encrypted:
            return config

        outer_msgpack = aes_cfb_decrypt(b64decode_any(encrypted), OUTER_KEY)
        outer = msgpack_unpack(outer_msgpack)
        locked_app = outer.get("LockedAppConfig", {}) if isinstance(outer, dict) else {}
        inner_blob = outer.get("EncryptedLockedConfig", b"") if isinstance(outer, dict) else b""

        decrypted_inner = None
        if isinstance(inner_blob, bytes) and inner_blob:
            inner_msgpack = aes_cfb_decrypt(inner_blob, INNER_KEY)
            inner = msgpack_unpack(inner_msgpack)
            decrypted_inner = decrypt_inner_fields(inner)

        config["decryptedLockedConfig"] = {
            "LockedAppConfig": json_safe(locked_app),
            "DecryptedInnerConfig": decrypted_inner,
        }
        return config
    except DarkConfigError:
        raise
    except Exception as exc:
        raise DarkConfigError("Could not parse or decrypt this .dark file.") from exc


class DarkConfigError(ValueError):
    """Raised when a `.dark` export cannot be parsed, decrypted, or unlocked."""


def build_unlocked_dark_uri(result: dict[str, Any]) -> str:
    """Convert a processed config dict back into a `darktunnel://` URI string."""
    unlocked_json = create_unlocked_config(result)
    unlocked_text = json.dumps(unlocked_json, separators=(",", ":"))
    b64_encoded = base64.b64encode(unlocked_text.encode("utf-8")).decode("utf-8")
    return f"darktunnel://{b64_encoded}"
