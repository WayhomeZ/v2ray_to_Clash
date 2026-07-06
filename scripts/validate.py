#!/usr/bin/env python3
"""Validate generated Clash/Mihomo YAML files before deployment."""
import sys
import re
import yaml
import urllib.parse

VALID_ALPN_PROTOCOLS = {'h2', 'h3', 'http/1.1', 'http/1.0', 'h2c'}
REQUIRED_FILES = ['docs/proxies.yaml', 'docs/config_monolithic.yaml']


def validate_proxy(proxy, filename):
    errors = []
    name = proxy.get('name', '<unnamed>')

    # Validate ws-opts.path
    ws_opts = proxy.get('ws-opts')
    if isinstance(ws_opts, dict):
        path = ws_opts.get('path')
        if isinstance(path, str):
            decoded = urllib.parse.unquote(path)
            if '//' in decoded or '%' in path:
                errors.append(f"[{filename}] {name}: invalid ws-opts.path '{path}'")

    # Validate alpn
    alpn = proxy.get('alpn')
    if alpn is not None:
        if not isinstance(alpn, list):
            errors.append(f"[{filename}] {name}: alpn must be a list, got {type(alpn).__name__}")
        else:
            for item in alpn:
                if not isinstance(item, str):
                    errors.append(f"[{filename}] {name}: alpn item must be string, got {type(item).__name__}")
                elif urllib.parse.unquote(item) not in VALID_ALPN_PROTOCOLS:
                    errors.append(f"[{filename}] {name}: invalid alpn value '{item}'")

    return errors


def validate_file(path):
    errors = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"[{path}] YAML parse error: {e}"]
    except FileNotFoundError:
        return [f"[{path}] file not found"]

    if not isinstance(data, dict):
        return [f"[{path}] top-level structure is not a mapping"]

    proxies = data.get('proxies')
    if not isinstance(proxies, list) or len(proxies) == 0:
        errors.append(f"[{path}] proxies list is missing or empty")
        return errors

    for proxy in proxies:
        if not isinstance(proxy, dict):
            errors.append(f"[{path}] non-mapping proxy entry found")
            continue
        errors.extend(validate_proxy(proxy, path))

    return errors


def main():
    all_errors = []
    for path in REQUIRED_FILES:
        all_errors.extend(validate_file(path))

    if all_errors:
        print("Validation failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("Validation passed: all generated YAML files look valid.")


if __name__ == '__main__':
    main()
