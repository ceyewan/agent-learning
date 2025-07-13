import asyncio
import base64
import hashlib
import json
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, urlunparse, parse_qs

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.exceptions import FastMCPError
from http.server import BaseHTTPRequestHandler, HTTPServer

# 配置
REDIRECT_HOST = "127.0.0.1"
REDIRECT_PORT = 28256
REDIRECT_PATH = "/oauth/callback"
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{REDIRECT_PATH}"

# 本地存储
DATA_DIR = Path("mcp_credentials")
CLIENT_INFO_FILE = DATA_DIR / "client_info.json"
TOKEN_DATA_FILE = DATA_DIR / "token_data.json"

TOKEN_EXPIRATION_BUFFER = 300  # 5 minutes

# 全局变量
authorization_code_holder = {"code": None, "error": None}
auth_state = {"status": "idle", "auth_url": None, "tools": None, "error": None}

app = FastAPI(title="MCP OAuth Service", version="1.0.0")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 数据模型
class AuthRequest(BaseModel):
    mcp_url: str

class AuthResponse(BaseModel):
    auth_url: str
    status: str

class StatusResponse(BaseModel):
    status: str
    tools: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class ToolInfo(BaseModel):
    name: str
    description: str

# 工具函数
def _save_json(filepath: Path, data: Dict[str, Any]):
    """将字典以JSON格式保存到文件。"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def _load_json(filepath: Path) -> Optional[Dict[str, Any]]:
    """从文件加载JSON数据。"""
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_token_expired(token_info: Dict[str, Any]) -> bool:
    """检查访问令牌是否已过期或即将过期。"""
    if "retrieved_at" not in token_info or "expires_in" not in token_info:
        return True
    expires_at = token_info["retrieved_at"] + token_info["expires_in"]
    return time.time() > (expires_at - TOKEN_EXPIRATION_BUFFER)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """OAuth回调处理器"""
    
    def do_GET(self):
        global authorization_code_holder, auth_state
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == REDIRECT_PATH:
            query_params = parse_qs(parsed_path.query)
            
            if 'error' in query_params:
                error_desc = query_params.get('error_description', [query_params['error'][0]])[0]
                authorization_code_holder['error'] = error_desc
                auth_state["status"] = "error"
                auth_state["error"] = error_desc
                message = f"<h1>认证失败</h1><p>错误: {error_desc}</p><p>您可以关闭此浏览器标签页。</p>"
            elif 'code' in query_params:
                authorization_code_holder['code'] = query_params['code'][0]
                auth_state["status"] = "processing"
                message = "<h1>认证成功!</h1><p>正在处理认证信息，请稍候...</p><p>您可以关闭此浏览器标签页。</p>"
            else:
                error_msg = "回调中缺少'code'或'error'参数"
                authorization_code_holder['error'] = error_msg
                auth_state["status"] = "error"
                auth_state["error"] = error_msg
                message = "<h1>无效的回调</h1>"
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode('utf-8'))
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_error(404, "Not Found")

def generate_pkce():
    """生成PKCE代码"""
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

async def perform_oauth_flow(mcp_url: str):
    """执行OAuth流程"""
    global authorization_code_holder, auth_state
    
    try:
        # 重置状态
        authorization_code_holder = {"code": None, "error": None}
        
        # 服务发现
        parsed_base_url = urlparse(mcp_url)
        discovery_url = urlunparse(
            (parsed_base_url.scheme, parsed_base_url.netloc, '/.well-known/oauth-authorization-server', '', '', ''))
        
        response = requests.get(discovery_url, timeout=10)
        response.raise_for_status()
        auth_server_info = response.json()
        
        registration_endpoint = auth_server_info['registration_endpoint']
        authorization_endpoint = auth_server_info['authorization_endpoint']
        token_endpoint = auth_server_info['token_endpoint']
        
        # 动态客户端注册
        reg_payload = {
            "redirect_uris": [REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "MCP Web Client"
        }
        
        response = requests.post(registration_endpoint, json=reg_payload, timeout=10)
        response.raise_for_status()
        client_info = response.json()
        client_id = client_info['client_id']
        client_info['token_endpoint'] = token_endpoint
        
        # 生成PKCE
        code_verifier, code_challenge = generate_pkce()
        
        # 启动回调服务器
        httpd = HTTPServer((REDIRECT_HOST, REDIRECT_PORT), OAuthCallbackHandler)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # 构建授权URL
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'redirect_uri': REDIRECT_URI
        }
        
        req = requests.Request('GET', authorization_endpoint, params=auth_params).prepare()
        auth_url = req.url
        
        # 更新状态
        auth_state["status"] = "waiting_for_auth"
        auth_state["auth_url"] = auth_url
        
        # 等待用户授权
        while authorization_code_holder['code'] is None and authorization_code_holder['error'] is None:
            await asyncio.sleep(1)
        
        if authorization_code_holder['error']:
            raise RuntimeError(f"认证失败: {authorization_code_holder['error']}")
        
        auth_code = authorization_code_holder['code']
        
        # 令牌交换
        token_payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': REDIRECT_URI,
            'client_id': client_id,
            'code_verifier': code_verifier
        }
        
        response = requests.post(token_endpoint, data=token_payload, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        token_data["retrieved_at"] = time.time()
        
        # 保存认证信息
        _save_json(CLIENT_INFO_FILE, client_info)
        _save_json(TOKEN_DATA_FILE, token_data)
        
        # 获取工具列表
        tools = await get_tools_list(mcp_url, token_data["access_token"])
        
        auth_state["status"] = "success"
        auth_state["tools"] = tools
        
    except Exception as e:
        auth_state["status"] = "error"
        auth_state["error"] = str(e)

async def get_tools_list(mcp_url: str, access_token: str) -> List[Dict[str, Any]]:
    """获取MCP工具列表"""
    try:
        auth_handler = BearerAuth(access_token)
        async with Client(mcp_url, auth=auth_handler) as client:
            tools = await client.list_tools()
            return [{"name": tool.name, "description": tool.description} for tool in tools]
    except Exception as e:
        print(f"获取工具列表失败: {e}")
        return []

# API路由
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """返回主页面"""
    return HTMLResponse(content=open("static/index.html").read())

@app.post("/api/start-auth", response_model=AuthResponse)
async def start_auth(request: AuthRequest):
    """启动OAuth认证流程"""
    global auth_state
    
    if auth_state["status"] in ["waiting_for_auth", "processing"]:
        raise HTTPException(status_code=400, detail="认证流程正在进行中")
    
    # 重置状态
    auth_state = {"status": "idle", "auth_url": None, "tools": None, "error": None}
    
    # 在后台启动OAuth流程
    asyncio.create_task(perform_oauth_flow(request.mcp_url))
    
    # 等待auth_url生成
    max_wait = 30  # 最多等待30秒
    waited = 0
    while auth_state["auth_url"] is None and auth_state["status"] != "error" and waited < max_wait:
        await asyncio.sleep(0.5)
        waited += 0.5
    
    if auth_state["status"] == "error":
        raise HTTPException(status_code=400, detail=auth_state["error"])
    
    if auth_state["auth_url"] is None:
        raise HTTPException(status_code=500, detail="生成认证URL超时")
    
    return AuthResponse(auth_url=auth_state["auth_url"], status=auth_state["status"])

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """获取认证状态"""
    return StatusResponse(
        status=auth_state["status"],
        tools=auth_state.get("tools"),
        error=auth_state.get("error")
    )

@app.get("/api/tools")
async def get_tools():
    """获取工具列表"""
    if auth_state["status"] != "success" or not auth_state["tools"]:
        raise HTTPException(status_code=400, detail="认证未完成或工具列表为空")
    
    return {"tools": auth_state["tools"]}

if __name__ == "__main__":
    import uvicorn
    
    # 创建静态文件目录
    Path("static").mkdir(exist_ok=True)
    
    print("启动MCP OAuth服务...")
    print("访问 http://localhost:8000 来使用Web界面")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
