"""
时区修复验证脚本
测试所有时间相关的函数是否正确使用 Asia/Shanghai 时区
"""
from datetime import datetime, timedelta
from shared.timezone_utils import now_shanghai, format_shanghai_time

def test_timezone():
    """测试时区函数"""
    print("=" * 60)
    print("时区修复验证")
    print("=" * 60)
    
    # 1. 测试 now_shanghai()
    print("\n1. 测试 now_shanghai():")
    now = now_shanghai()
    print(f"   当前时间: {now}")
    print(f"   类型: {type(now)}")
    print(f"   时区信息: {now.tzinfo}")
    print(f"   是否为 naive: {now.tzinfo is None}")
    
    # 2. 测试时间运算
    print("\n2. 测试时间运算:")
    future = now + timedelta(hours=1)
    print(f"   1小时后: {future}")
    print(f"   可以正常运算: ✅")
    
    # 3. 测试格式化
    print("\n3. 测试格式化:")
    formatted = format_shanghai_time()
    print(f"   格式化时间: {formatted}")
    print(f"   ISO格式: {now.isoformat()}")
    
    # 4. 对比 UTC 时间
    print("\n4. 对比 UTC 时间:")
    utc_now = datetime.utcnow()
    print(f"   UTC 时间: {utc_now}")
    print(f"   上海时间: {now}")
    diff = (now - utc_now).total_seconds() / 3600
    print(f"   时差: {diff:.1f} 小时")
    print(f"   预期时差: 8 小时")
    print(f"   时差正确: {'✅' if abs(diff - 8) < 0.1 else '❌'}")
    
    # 5. 测试数据库兼容性
    print("\n5. 测试数据库兼容性:")
    print(f"   naive datetime: {now.tzinfo is None}")
    print(f"   可用于 PostgreSQL TIMESTAMP: {'✅' if now.tzinfo is None else '❌'}")
    print(f"   可用于 asyncpg: {'✅' if now.tzinfo is None else '❌'}")
    
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_timezone()
