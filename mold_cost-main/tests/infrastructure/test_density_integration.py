"""
测试 density_search 集成
验证重量计算是否正确获取密度数据
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from api_gateway.database import db
from scripts.search import density_search, base_itemcode_search
from scripts.calculate import price_weight


async def test_density_integration(job_id: str):
    """测试密度数据集成"""
    print(f"\n{'='*80}")
    print(f"测试 density_search 集成 (job_id: {job_id})")
    print(f"{'='*80}\n")
    
    try:
        # 初始化数据库连接
        await db.connect()
        
        # Step 1: 测试 density_search
        print("[Step 1] 测试 density_search...")
        density_result = await density_search.search_by_job_id(job_id)
        
        if density_result.get("density_data"):
            print(f"✓ 找到 {len(density_result['density_data'])} 条密度数据")
            for item in density_result["density_data"][:5]:  # 只显示前5条
                print(f"  - {item['sub_category']}: {item['price']} {item['unit']}")
        else:
            print("✗ 未找到密度数据")
            return
        
        # Step 2: 测试 base_itemcode_search
        print("\n[Step 2] 测试 base_itemcode_search...")
        base_result = await base_itemcode_search.search_by_job_id(job_id)
        
        if base_result.get("parts"):
            print(f"✓ 找到 {len(base_result['parts'])} 个零件")
            for part in base_result["parts"][:3]:  # 只显示前3个
                print(f"  - {part['part_name']}: {part.get('material', 'N/A')} "
                      f"({part.get('length_mm', 0)}x{part.get('width_mm', 0)}x{part.get('thickness_mm', 0)}mm)")
        else:
            print("✗ 未找到零件数据")
            return
        
        # Step 3: 测试重量计算
        print("\n[Step 3] 测试重量计算...")
        search_data = {
            "base_itemcode": base_result,
            "density": density_result
        }
        
        weight_result = await price_weight.calculate(search_data, job_id)
        
        if weight_result.get("results"):
            print(f"✓ 计算了 {len(weight_result['results'])} 个零件的重量")
            for result in weight_result["results"][:3]:  # 只显示前3个
                if "error" not in result:
                    print(f"  - {result['part_name']}: {result.get('weight', 0):.3f} kg")
                else:
                    print(f"  - {result['part_name']}: 错误 - {result['error']}")
        else:
            print("✗ 重量计算失败")
            return
        
        # Step 4: 验证数据库中的重量字段
        print("\n[Step 4] 验证数据库中的重量字段...")
        sql = """
            SELECT subgraph_id, part_name, weight_kg
            FROM subgraphs
            WHERE job_id = $1::uuid
            ORDER BY subgraph_id
            LIMIT 5
        """
        rows = await db.fetch_all(sql, job_id)
        
        if rows:
            print(f"✓ 数据库中有 {len(rows)} 条记录（显示前5条）")
            for row in rows:
                weight = row["weight_kg"] or 0
                status = "✓" if weight > 0 else "✗"
                print(f"  {status} {row['part_name']}: {weight:.3f} kg")
        else:
            print("✗ 数据库中没有找到记录")
        
        print(f"\n{'='*80}")
        print("测试完成！")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_density_integration.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    asyncio.run(test_density_integration(job_id))
