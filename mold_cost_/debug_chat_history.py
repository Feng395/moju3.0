"""
调试聊天历史数据

检查数据库中是否有历史消息
"""
import asyncio
import sys
from sqlalchemy import text
from shared.database import get_db


async def check_chat_history(job_id: str):
    """检查指定 job_id 的聊天历史"""
    print(f"=" * 60)
    print(f"检查聊天历史: job_id={job_id}")
    print(f"=" * 60)
    
    async for db in get_db():
        try:
            # 1. 检查会话是否存在
            print(f"\n1️⃣ 检查会话...")
            result = await db.execute(
                text("SELECT * FROM chat_sessions WHERE session_id = :session_id"),
                {"session_id": job_id}
            )
            session = result.fetchone()
            
            if session:
                print(f"✅ 会话存在:")
                print(f"   session_id: {session[0]}")
                print(f"   job_id: {session[1]}")
                print(f"   user_id: {session[2]}")
                print(f"   created_at: {session[3]}")
                print(f"   status: {session[5]}")
            else:
                print(f"❌ 会话不存在")
                return
            
            # 2. 检查消息数量
            print(f"\n2️⃣ 检查消息数量...")
            result = await db.execute(
                text("SELECT COUNT(*) FROM chat_messages WHERE session_id = :session_id"),
                {"session_id": job_id}
            )
            count = result.scalar()
            print(f"📊 消息总数: {count}")
            
            if count == 0:
                print(f"⚠️  没有消息记录")
                return
            
            # 3. 查询最近的消息
            print(f"\n3️⃣ 查询最近的消息...")
            result = await db.execute(
                text("""
                    SELECT message_id, role, content, timestamp
                    FROM chat_messages
                    WHERE session_id = :session_id
                    ORDER BY timestamp DESC, message_id DESC
                    LIMIT 10
                """),
                {"session_id": job_id}
            )
            
            messages = result.fetchall()
            
            print(f"📝 最近 {len(messages)} 条消息:")
            for msg in messages:
                print(f"\n   [{msg[1]}] {msg[3]}")
                print(f"   {msg[2][:100]}...")
            
            # 4. 检查是否有子图ID
            print(f"\n4️⃣ 检查消息中的子图ID...")
            import re
            pattern = r'\b([A-Z]{2}[-_]?\d{2})\b'
            
            found_subgraphs = []
            for msg in messages:
                content = msg[2]
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        subgraph_id = match.upper().replace("_", "-")
                        found_subgraphs.append({
                            "subgraph_id": subgraph_id,
                            "role": msg[1],
                            "content": content[:50]
                        })
            
            if found_subgraphs:
                print(f"✅ 找到 {len(found_subgraphs)} 个子图ID:")
                for item in found_subgraphs:
                    print(f"   - {item['subgraph_id']} (来自 {item['role']} 消息)")
                    print(f"     {item['content']}...")
            else:
                print(f"❌ 未找到子图ID")
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            break


async def list_all_sessions():
    """列出所有会话"""
    print(f"=" * 60)
    print(f"列出所有会话")
    print(f"=" * 60)
    
    async for db in get_db():
        try:
            result = await db.execute(
                text("""
                    SELECT s.session_id, s.job_id, s.user_id, s.created_at, s.status,
                           COUNT(m.message_id) as message_count
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    GROUP BY s.session_id, s.job_id, s.user_id, s.created_at, s.status
                    ORDER BY s.created_at DESC
                    LIMIT 10
                """)
            )
            
            sessions = result.fetchall()
            
            if sessions:
                print(f"\n📋 最近 {len(sessions)} 个会话:")
                for s in sessions:
                    print(f"\n   session_id: {s[0]}")
                    print(f"   job_id: {s[1]}")
                    print(f"   user_id: {s[2]}")
                    print(f"   created_at: {s[3]}")
                    print(f"   status: {s[4]}")
                    print(f"   消息数: {s[5]}")
            else:
                print(f"❌ 没有会话记录")
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            break


async def main():
    """主函数"""
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        await check_chat_history(job_id)
    else:
        print("用法:")
        print("  python debug_chat_history.py <job_id>")
        print()
        print("或者列出所有会话:")
        await list_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())
