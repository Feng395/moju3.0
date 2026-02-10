"""
WebSocket基础连接测试
测试第一阶段：基础WebSocket连接
"""
import asyncio
import websockets
import json
from datetime import datetime

async def test_basic_connection():
    """测试基础连接"""
    job_id = "test-job-123"
    uri = f"ws://localhost:8000/ws/{job_id}"
    
    print("=" * 60)
    print("WebSocket基础连接测试")
    print("=" * 60)
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ 连接成功: {uri}")
            
            # 1. 接收欢迎消息
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"\n📨 收到欢迎消息:")
            print(json.dumps(welcome_data, indent=2, ensure_ascii=False))
            
            # 2. 发送测试消息
            test_message = "Hello WebSocket!"
            print(f"\n📤 发送消息: {test_message}")
            await websocket.send(test_message)
            
            # 3. 接收回显
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"\n📥 收到回显:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # 4. 发送JSON消息
            json_message = {
                "type": "test",
                "content": "这是一条JSON消息",
                "timestamp": datetime.now().isoformat()
            }
            print(f"\n📤 发送JSON消息:")
            print(json.dumps(json_message, indent=2, ensure_ascii=False))
            await websocket.send(json.dumps(json_message))
            
            # 5. 接收JSON回显
            json_response = await websocket.recv()
            json_response_data = json.loads(json_response)
            print(f"\n📥 收到JSON回显:")
            print(json.dumps(json_response_data, indent=2, ensure_ascii=False))
            
            # 6. 测试ping-pong
            print(f"\n💓 测试心跳...")
            await websocket.send(json.dumps({"type": "ping"}))
            pong = await websocket.recv()
            pong_data = json.loads(pong)
            print(f"✅ 收到pong: {pong_data['timestamp']}")
            
            print("\n" + "=" * 60)
            print("✅ 所有测试通过！")
            print("=" * 60)
    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ 连接关闭: {e}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_connections():
    """测试多个连接"""
    job_id = "test-job-456"
    uri = f"ws://localhost:8000/ws/{job_id}"
    
    print("\n" + "=" * 60)
    print("多连接测试")
    print("=" * 60)
    
    try:
        # 建立3个连接
        connections = []
        for i in range(3):
            ws = await websockets.connect(uri)
            connections.append(ws)
            welcome = await ws.recv()
            print(f"✅ 连接{i+1}建立成功")
        
        # 从第一个连接发送消息
        await connections[0].send("广播测试消息")
        print(f"\n📤 从连接1发送消息")
        
        # 所有连接都应该收到回显
        for i, ws in enumerate(connections):
            response = await ws.recv()
            print(f"📥 连接{i+1}收到消息")
        
        # 关闭所有连接
        for i, ws in enumerate(connections):
            await ws.close()
            print(f"❌ 连接{i+1}已关闭")
        
        print("\n✅ 多连接测试通过！")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_reconnection():
    """测试重连"""
    job_id = "test-job-789"
    uri = f"ws://localhost:8000/ws/{job_id}"
    
    print("\n" + "=" * 60)
    print("重连测试")
    print("=" * 60)
    
    try:
        # 第一次连接
        async with websockets.connect(uri) as ws1:
            print("✅ 第一次连接成功")
            await ws1.recv()  # 接收欢迎消息
        
        print("❌ 第一次连接已断开")
        
        # 等待1秒
        await asyncio.sleep(1)
        
        # 第二次连接
        async with websockets.connect(uri) as ws2:
            print("✅ 第二次连接成功（重连）")
            await ws2.recv()  # 接收欢迎消息
        
        print("✅ 重连测试通过！")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """运行所有测试"""
    print("\n🧪 开始WebSocket测试...\n")
    
    # 测试1：基础连接
    await test_basic_connection()
    
    # 等待1秒
    await asyncio.sleep(1)
    
    # 测试2：多连接
    await test_multiple_connections()
    
    # 等待1秒
    await asyncio.sleep(1)
    
    # 测试3：重连
    await test_reconnection()
    
    print("\n🎉 所有测试完成！\n")

if __name__ == "__main__":
    asyncio.run(main())
