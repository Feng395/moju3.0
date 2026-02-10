"""
测试导入是否正常
"""
import sys
print("Python 路径:")
for p in sys.path:
    print(f"  {p}")

print("\n尝试导入 shared.validators...")

try:
    from shared.validators import (
        FieldValidator,
        BusinessValidator,
        ModificationValidator,
        ValidationResult
    )
    print("✅ 导入成功！")
    
    # 测试一个简单的验证
    is_valid, error = FieldValidator.validate_material("P20")
    print(f"\n测试验证: validate_material('P20')")
    print(f"结果: is_valid={is_valid}, error={error}")
    
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
