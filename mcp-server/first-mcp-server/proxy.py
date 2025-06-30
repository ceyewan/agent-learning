#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP SSE 代理服务器 - 优化版本
修复 SSE 流处理和连接管理问题
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime
from aiohttp import web, ClientSession, ClientTimeout
from aiohttp.web_response import StreamResponse
from typing import Optional, Dict, Any
import uuid
import os

class MCPProxyLogger:
    """MCP 通信日志记录器"""
    
    def __init__(self, log_dir: str = "mcp_logs"):
        self.log_dir = log_dir
        self.ensure_log_directory()
        self.setup_logger()
    
    def ensure_log_directory(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def setup_logger(self):
        """设置日志记录器"""
        log_filename = f"mcp_proxy_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(self.log_dir, log_filename)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filepath, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MCPProxy')
    
    def log_request(self, session_id: str, method: str, url: str, 
                   headers: Dict, body: Optional[str] = None):
        """记录客户端请求"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'direction': 'CLIENT_TO_PROXY',
            'type': 'REQUEST',
            'method': method,
            'url': url,
            'headers': dict(headers),
            'body': body
        }
        self.logger.info(f"REQUEST: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
    
    def log_response(self, session_id: str, status: int, headers: Dict, 
                    body: Optional[str] = None):
        """记录服务器响应"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'direction': 'SERVER_TO_PROXY',
            'type': 'RESPONSE',
            'status': status,
            'headers': dict(headers),
            'body': body
        }
        self.logger.info(f"RESPONSE: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
    
    def log_sse_event(self, session_id: str, event_type: str, data: str):
        """记录 SSE 事件"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'direction': 'SERVER_TO_CLIENT',
            'type': 'SSE_EVENT',
            'event_type': event_type,
            'data': data
        }
        self.logger.info(f"SSE_EVENT: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
    
    def log_connection_status(self, session_id: str, status: str, details: str = ""):
        """记录连接状态"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'type': 'CONNECTION_STATUS',
            'status': status,
            'details': details
        }
        self.logger.info(f"CONNECTION: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
    
    def log_error(self, session_id: str, error: str, details: Optional[Dict] = None):
        """记录错误信息"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'type': 'ERROR',
            'error': error,
            'details': details or {}
        }
        self.logger.error(f"ERROR: {json.dumps(log_data, ensure_ascii=False, indent=2)}")

class MCPSSEProxy:
    """MCP SSE 代理服务器 - 优化版"""
    
    def __init__(self, proxy_port: int = 8000, target_host: str = "localhost", 
                 target_port: int = 8080):
        self.proxy_port = proxy_port
        self.target_host = target_host
        self.target_port = target_port
        self.target_base_url = f"http://{target_host}:{target_port}"
        
        # 初始化日志记录器
        self.logger = MCPProxyLogger()
        
        # 创建 aiohttp 应用
        self.app = web.Application()
        self.setup_routes()
        
        # 活跃连接跟踪
        self.active_connections = {}
    
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_route('*', '/{path:.*}', self.handle_request)
    
    async def handle_request(self, request: web.Request) -> web.StreamResponse:
        """处理所有传入的请求"""
        session_id = str(uuid.uuid4())[:8]
        
        # 记录连接建立
        self.logger.log_connection_status(session_id, "ESTABLISHED", 
                                        f"Client: {request.remote} -> Proxy: {self.proxy_port}")
        
        try:
            # 读取请求体
            body_text = None
            if request.can_read_body:
                body_bytes = await request.read()
                body_text = body_bytes.decode('utf-8') if body_bytes else None
            
            # 记录请求
            self.logger.log_request(
                session_id=session_id,
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                body=body_text
            )
            
            # 检查是否为 SSE 请求
            accept_header = request.headers.get('Accept', '').lower()
            if 'text/event-stream' in accept_header:
                return await self.handle_sse_request(request, session_id)
            else:
                return await self.handle_http_request(request, session_id, body_text)
                
        except Exception as e:
            self.logger.log_error(session_id, f"请求处理失败: {str(e)}")
            return web.Response(
                status=500,
                text=f"代理服务器内部错误: {str(e)}",
                content_type='text/plain; charset=utf-8'
            )
        finally:
            # 记录连接关闭
            self.logger.log_connection_status(session_id, "CLOSED")
    
    async def handle_http_request(self, request: web.Request, session_id: str, 
                                body_text: Optional[str]) -> web.Response:
        """处理普通 HTTP 请求"""
        target_url = f"{self.target_base_url}{request.path_qs}"
        
        # 准备转发头部
        forward_headers = dict(request.headers)
        headers_to_remove = ['host', 'content-length']
        for header in headers_to_remove:
            forward_headers.pop(header, None)
        
        try:
            timeout = ClientTimeout(total=30)
            async with ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=forward_headers,
                    data=body_text.encode('utf-8') if body_text else None
                ) as response:
                    
                    response_body = await response.text()
                    
                    # 记录响应
                    self.logger.log_response(
                        session_id=session_id,
                        status=response.status,
                        headers=dict(response.headers),
                        body=response_body
                    )
                    
                    return web.Response(
                        status=response.status,
                        text=response_body,
                        headers=response.headers,
                        content_type=response.content_type
                    )
                    
        except Exception as e:
            self.logger.log_error(session_id, f"HTTP请求转发失败: {str(e)}")
            return web.Response(
                status=502,
                text=f"无法连接到目标服务器: {str(e)}",
                content_type='text/plain; charset=utf-8'
            )
    
    async def handle_sse_request(self, request: web.Request, session_id: str) -> StreamResponse:
        """处理 SSE 请求 - 优化版"""
        target_url = f"{self.target_base_url}{request.path_qs}"
        
        # 记录 SSE 连接开始
        self.logger.log_connection_status(session_id, "SSE_STARTED", target_url)
        
        # 创建流响应
        response = StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control',
                'X-Accel-Buffering': 'no'  # 禁用 nginx 缓冲
            }
        )
        
        await response.prepare(request)
        
        client_session = None
        try:
            # 准备转发头部
            forward_headers = dict(request.headers)
            forward_headers.pop('host', None)
            
            # 创建持久客户端会话
            timeout = ClientTimeout(total=None, sock_read=None)
            client_session = ClientSession(timeout=timeout)
            self.active_connections[session_id] = client_session
            
            async with client_session.get(target_url, headers=forward_headers) as target_response:
                
                # 记录目标服务器响应
                self.logger.log_response(
                    session_id=session_id,
                    status=target_response.status,
                    headers=dict(target_response.headers),
                    body="[SSE Stream Started]"
                )
                
                # 处理 SSE 数据流
                buffer = ""
                async for chunk in target_response.content.iter_chunked(1024):
                    try:
                        chunk_text = chunk.decode('utf-8')
                        buffer += chunk_text
                        
                        # 按行处理 SSE 数据
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            
                            if line.strip():
                                # 解析并记录 SSE 事件
                                event_type, event_data = self.parse_sse_line(line.strip())
                                self.logger.log_sse_event(session_id, event_type, event_data)
                            
                            # 转发原始行到客户端
                            line_with_newline = line + '\n'
                            await response.write(line_with_newline.encode('utf-8'))
                            
                        # 处理剩余的不完整行
                        if buffer and not buffer.endswith('\n'):
                            await response.write(buffer.encode('utf-8'))
                            buffer = ""
                            
                    except UnicodeDecodeError as e:
                        self.logger.log_error(session_id, f"SSE数据解码失败: {str(e)}")
                        continue
                    except Exception as e:
                        self.logger.log_error(session_id, f"SSE数据处理失败: {str(e)}")
                        break
                
        except asyncio.CancelledError:
            self.logger.log_connection_status(session_id, "SSE_CANCELLED", "客户端断开连接")
        except Exception as e:
            self.logger.log_error(session_id, f"SSE流处理失败: {str(e)}")
            # 发送错误事件到客户端
            error_event = f"event: error\ndata: {{\"error\": \"代理服务器错误: {str(e)}\"}}\n\n"
            try:
                await response.write(error_event.encode('utf-8'))
            except:
                pass
        finally:
            # 清理连接
            if session_id in self.active_connections:
                if client_session and not client_session.closed:
                    await client_session.close()
                del self.active_connections[session_id]
            
            self.logger.log_connection_status(session_id, "SSE_ENDED")
        
        return response
    
    def parse_sse_line(self, line: str) -> tuple[str, str]:
        """解析 SSE 行数据"""
        if line.startswith('event:'):
            return 'event', line[6:].strip()
        elif line.startswith('data:'):
            return 'data', line[5:].strip()
        elif line.startswith('id:'):
            return 'id', line[3:].strip()
        elif line.startswith('retry:'):
            return 'retry', line[6:].strip()
        elif line == '':
            return 'separator', ''
        else:
            return 'raw', line
    
    async def start_server(self):
        """启动代理服务器"""
        print(f"🚀 MCP SSE 代理服务器启动中...")
        print(f"📡 代理端口: {self.proxy_port}")
        print(f"🎯 目标服务器: {self.target_base_url}")
        print(f"📝 日志目录: {self.logger.log_dir}")
        print(f"🔗 访问地址: http://localhost:{self.proxy_port}")
        print("=" * 50)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', self.proxy_port)
        await site.start()
        
        print(f"✅ 代理服务器已启动，监听端口 {self.proxy_port}")
        print(f"📊 连接状态: 等待客户端连接...")
        
        try:
            while True:
                # 定期报告活跃连接数
                active_count = len(self.active_connections)
                if active_count > 0:
                    print(f"📈 活跃 SSE 连接数: {active_count}")
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭服务器...")
            
            # 关闭所有活跃连接
            for session_id, session in self.active_connections.items():
                try:
                    await session.close()
                except:
                    pass
            
            await runner.cleanup()
            print("✅ 代理服务器已停止")

async def main():
    """主函数"""
    proxy = MCPSSEProxy(
        proxy_port=8000,
        target_host="localhost",
        target_port=8080
    )
    
    await proxy.start_server()

if __name__ == "__main__":
    asyncio.run(main())
