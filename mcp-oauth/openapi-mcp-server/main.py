import asyncio
import base64
import hashlib
import json
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs

import requests
from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.exceptions import FastMCPError

# --- 配置 ---
# 请将这里替换为您的 MCP Server 的基础 URL
MCP_SERVER_BASE_URL = "https://openapi-mcp.cn-hangzhou.aliyuncs.com/accounts/1840724847576507/custom/yingxi-test/id/21HFYMWbiIH1zuTx/mcp"

# 本地回调服务器配置
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 28256
REDIRECT_PATH = "/oauth/callback"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"

# 本地存储文件
DATA_DIR = Path("mcp_credentials")
CLIENT_INFO_FILE = DATA_DIR / "client_info.json"
TOKEN_DATA_FILE = DATA_DIR / "token_data.json"

# 令牌过期前的缓冲时间（秒），提前这么多秒进行刷新
TOKEN_EXPIRATION_BUFFER = 300  # 5 minutes

# 全局变量，用于在主线程和HTTP服务器线程间传递授权码
authorization_code_holder = {"code": None, "error": None}


# --- 模块 1: 文件和状态管理 ---

def _save_json(filepath: Path, data: Dict[str, Any]):
    """将字典以JSON格式保存到文件。"""
    print(f"[*] 正在保存数据到: {filepath}")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def _load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """从文件加载JSON数据。"""
    if not filepath.exists():
        return None
    print(f"[*] 正在从文件加载数据: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_token_expired(token_info: Dict[str, Any]) -> bool:
    """检查访问令牌是否已过期或即将过期。"""
    if "retrieved_at" not in token_info or "expires_in" not in token_info:
        return True  # 如果缺少必要信息，则认为已过期

    expires_at = token_info["retrieved_at"] + token_info["expires_in"]
    return time.time() > (expires_at - TOKEN_EXPIRATION_BUFFER)


# --- 模块 2: OAuth 核心流程 (包括刷新和完整认证) ---

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """一个简单的 HTTP 请求处理器，用于捕获 OAuth 回调。"""

    def do_GET(self):
        global authorization_code_holder
        parsed_path = urlparse(self.path)
        if parsed_path.path == REDIRECT_PATH:
            query_params = parse_qs(parsed_path.query)
            if 'error' in query_params:
                error_desc = query_params.get(
                    'error_description', [query_params['error'][0]])[0]
                authorization_code_holder['error'] = error_desc
                message = f"<h1>认证失败</h1><p>错误: {error_desc}</p>"
            elif 'code' in query_params:
                authorization_code_holder['code'] = query_params['code'][0]
                message = "<h1>认证成功!</h1><p>已获取授权码，您可以关闭此浏览器标签页。</p>"
            else:
                authorization_code_holder['error'] = "回调中缺少'code'或'error'参数"
                message = "<h1>无效的回调</h1>"

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode('utf-8'))
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_error(404, "Not Found")


def _perform_full_oauth_flow() -> Optional[Tuple[Dict, Dict]]:
    """执行完整的、需要用户交互的 OAuth 认证流程。"""
    print("\n--- 开始执行完整的 OAuth 认证流程 ---")

    try:
        # 步骤 1: 服务发现
        print("[1/5] 服务发现...")
        parsed_base_url = urlparse(MCP_SERVER_BASE_URL)
        discovery_url = urlunparse(
            (parsed_base_url.scheme, parsed_base_url.netloc, '/.well-known/oauth-authorization-server', '', '', ''))
        response = requests.get(discovery_url, timeout=10)
        response.raise_for_status()
        auth_server_info = response.json()
        registration_endpoint = auth_server_info['registration_endpoint']
        authorization_endpoint = auth_server_info['authorization_endpoint']
        token_endpoint = auth_server_info['token_endpoint']
        print("[+] 服务发现成功！")

        # 步骤 2: 动态客户端注册
        print("[2/5] 动态客户端注册...")
        reg_payload = {"redirect_uris": [REDIRECT_URI], "token_endpoint_auth_method": "none",
                       "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                       "client_name": "My Python MCP Agent"}
        response = requests.post(
            registration_endpoint, json=reg_payload, timeout=10)
        response.raise_for_status()
        client_info = response.json()
        client_id = client_info['client_id']
        # 将令牌端点也保存下来，供刷新时使用
        client_info['token_endpoint'] = token_endpoint
        print(f"[+] 客户端注册成功！Client ID: {client_id}")

        # 步骤 3: 生成 PKCE
        print("[3/5] 生成 PKCE 代码...")
        code_verifier = secrets.token_urlsafe(64)
        hashed = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(
            hashed).decode('utf-8').rstrip('=')
        print("[+] PKCE 代码已生成。")

        # 步骤 4: 用户授权
        print("[4/5] 等待用户授权...")
        httpd = HTTPServer((REDIRECT_HOST, REDIRECT_PORT),
                           _OAuthCallbackHandler)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        auth_params = {'response_type': 'code', 'client_id': client_id, 'code_challenge': code_challenge,
                       'code_challenge_method': 'S256', 'redirect_uri': REDIRECT_URI}
        req = requests.Request(
            'GET', authorization_endpoint, params=auth_params).prepare()
        webbrowser.open(req.url)
        print("\n>>> 请在打开的浏览器窗口中完成授权操作。 <<<")

        server_thread.join()  # 等待HTTP服务器关闭
        if authorization_code_holder['error']:
            raise RuntimeError(f"认证失败: {authorization_code_holder['error']}")
        auth_code = authorization_code_holder['code']
        print(f"[+] 成功捕获到授权码。")

        # 步骤 5: 令牌交换
        print("[5/5] 交换令牌...")
        token_payload = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': REDIRECT_URI,
                         'client_id': client_id, 'code_verifier': code_verifier}
        response = requests.post(
            token_endpoint, data=token_payload, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        print("[+] 成功获取令牌！")

        return client_info, token_data

    except requests.exceptions.RequestException as e:
        print(f"\n[!] 网络请求错误: {e}", file=sys.stderr)
        if e.response:
            print(f"    - 响应内容: {e.response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"\n[!] 发生未知错误: {e}", file=sys.stderr)
        return None


def refresh_access_token(client_info: Dict[str, Any], token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """使用刷新令牌获取新的访问令牌。"""
    print("[*] 访问令牌已过期，尝试刷新...")
    refresh_token = token_data.get("refresh_token")
    client_id = client_info.get("client_id")
    token_endpoint = client_info.get("token_endpoint")

    if not all([refresh_token, client_id, token_endpoint]):
        print(
            "[!] 缺少刷新所需的信息 (refresh_token, client_id, or token_endpoint)。", file=sys.stderr)
        return None

    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id
    }
    try:
        response = requests.post(token_endpoint, data=payload, timeout=10)
        response.raise_for_status()
        new_token_data = response.json()
        print("[+] 令牌刷新成功！")
        return new_token_data
    except requests.exceptions.RequestException as e:
        print(f"[!] 刷新令牌失败: {e}", file=sys.stderr)
        if e.response:
            print(f"    - 响应状态码: {e.response.status_code}", file=sys.stderr)
            print(f"    - 响应内容: {e.response.text}", file=sys.stderr)
        return None


# --- 模块 3: 凭证管理和 MCP 客户端 ---

async def get_mcp_credentials() -> Optional[Dict[str, Any]]:
    """
    管理和获取有效的MCP凭证。
    它会先尝试从文件加载，然后检查是否过期，如果过期则尝试刷新，
    如果所有尝试都失败，则启动完整的用户认证流程。
    """
    client_info = _load_json(CLIENT_INFO_FILE)
    token_data = _load_json(TOKEN_DATA_FILE)

    if client_info and token_data:
        if is_token_expired(token_data):
            new_token_data = refresh_access_token(client_info, token_data)
            if new_token_data:
                token_data = new_token_data
                token_data["retrieved_at"] = time.time()
                _save_json(TOKEN_DATA_FILE, token_data)
            else:
                print("[!] 刷新失败，需要重新进行完整认证。")
                client_info, token_data = None, None  # 标记为需要重新认证
        else:
            print("[+] 使用本地缓存的有效令牌。")

    if not (client_info and token_data):
        print("[*] 未找到有效的本地令牌，启动完整认证流程。")
        auth_result = _perform_full_oauth_flow()
        if not auth_result:
            return None  # 认证失败

        client_info, token_data = auth_result
        token_data["retrieved_at"] = time.time()

        # 将新获取的信息保存到文件
        _save_json(CLIENT_INFO_FILE, client_info)
        _save_json(TOKEN_DATA_FILE, token_data)

    return token_data


async def connect_and_list_tools(access_token: str):
    """使用给定的访问令牌连接到MCP服务器并列出工具。"""
    print("\n--- 正在连接到 MCP 服务器 ---")
    try:
        auth_handler = BearerAuth(access_token)
        async with Client(MCP_SERVER_BASE_URL, auth=auth_handler) as client:
            print("\n✅ 认证成功，已连接到服务器！")
            tools = await client.list_tools()
            print("\n🛠️  服务器可用工具列表:")
            if not tools:
                print("  - 未发现任何工具。")
            else:
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")

    except FastMCPError as e:
        if "Session termination failed" in str(e):
            print("\nℹ️  会话正常结束。注意：服务器不支持标准的会话终止请求，但这不影响操作结果。")
        else:
            print(f"\n❌ 操作过程中发生 MCP 错误: {e}", file=sys.stderr)
            print("   请检查服务器状态或认证信息是否正确。", file=sys.stderr)
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}", file=sys.stderr)


# --- 模块 4: 主程序入口 ---

async def main():
    """主执行函数。"""
    print("==============================================")
    print("      MCP 客户端认证与连接工具")
    print("==============================================")

    # 步骤 1: 获取有效凭证（自动处理加载、刷新或完整认证）
    token_info = await get_mcp_credentials()

    if not token_info or "access_token" not in token_info:
        print("\n[!] 未能获取到有效的访问令牌，程序退出。", file=sys.stderr)
        sys.exit(1)

    print("\n========================================================")
    print("✅ 凭证准备就绪！")
    print("========================================================")
    print("最终获取到的令牌信息:")
    print(json.dumps(token_info, indent=4))

    # 步骤 2: 使用获取到的令牌连接到MCP服务器
    await connect_and_list_tools(token_info["access_token"])

    print("\n程序执行完毕。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] 用户中断了程序。")
        sys.exit(0)
