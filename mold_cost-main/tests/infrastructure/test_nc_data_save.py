"""
测试 NC 数据保存格式
验证按子图保存的数据结构
"""
import json
from pathlib import Path
from datetime import datetime

def test_save_format():
    """测试新的保存格式"""
    
    # 读取原始的 NC 响应数据
    source_file = Path("logs/nc_responses/987b7efa-e924-4dc0-9fb4-567a75db717a_20260129_124833.json")
    
    if not source_file.exists():
        print(f"❌ 测试数据文件不存在: {source_file}")
        return
    
    with open(source_file, 'r', encoding='utf-8') as f:
        nc_result = json.load(f)
    
    # 模拟新的保存格式
    job_id = "test-job-id"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    json_output = nc_result.get("data", {}).get("json_output", {})
    
    # 构建完整的数据结构
    complete_data = {
        "job_id": job_id,
        "timestamp": timestamp,
        "task_id": nc_result.get("data", {}).get("task_id"),
        "execution_time": nc_result.get("data", {}).get("execution_time"),
        "total_subgraphs": len(json_output),
        "subgraphs": {}
    }
    
    # 遍历每个子图
    for subgraph_name, subgraph_data in json_output.items():
        # 提取子图短ID
        subgraph_short_id = extract_subgraph_id(subgraph_name)
        
        # 保存子图数据
        complete_data["subgraphs"][subgraph_short_id] = {
            "file_name": subgraph_name,
            "meta_data": subgraph_data.get("meta_data", {}),
            "operations": subgraph_data.get("operations", [])
        }
    
    # 保存到测试目录
    test_dir = Path("logs/nc_responses") / job_id
    test_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"nc_data_{job_id}_{timestamp}.json"
    filepath = test_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(complete_data, f, ensure_ascii=False, indent=2)
    
    print("=" * 80)
    print("NC 数据保存格式测试")
    print("=" * 80)
    print()
    print(f"✅ 数据已保存到: {filepath}")
    print()
    print(f"📊 数据统计:")
    print(f"  • 任务ID: {complete_data['job_id']}")
    print(f"  • 时间戳: {complete_data['timestamp']}")
    print(f"  • 子图总数: {complete_data['total_subgraphs']}")
    print(f"  • 执行时间: {complete_data['execution_time']} 秒")
    print()
    print(f"📦 子图列表:")
    for subgraph_id, subgraph_info in complete_data["subgraphs"].items():
        operations_count = len(subgraph_info["operations"])
        print(f"  • {subgraph_id:10s} → {operations_count:2d} 个操作 ({subgraph_info['file_name']})")
    print()
    
    # 显示第一个子图的详细数据示例
    first_subgraph_id = list(complete_data["subgraphs"].keys())[0]
    first_subgraph = complete_data["subgraphs"][first_subgraph_id]
    
    print(f"📋 子图详细数据示例 ({first_subgraph_id}):")
    print(f"  文件名: {first_subgraph['file_name']}")
    print(f"  元数据:")
    for key, value in first_subgraph["meta_data"].items():
        print(f"    • {key}: {value}")
    print()
    print(f"  操作列表 (前3个):")
    for i, op in enumerate(first_subgraph["operations"][:3]):
        op_name = op.get("operation_name", "")
        params = op.get("parameters", [])
        if params:
            time_value = params[0].get("value", 0)
            print(f"    {i+1}. {op_name:30s} → {time_value:.4f} 分钟")
    print()
    
    # 验证数据结构
    print("✅ 数据结构验证:")
    print(f"  • 包含 job_id: {'job_id' in complete_data}")
    print(f"  • 包含 timestamp: {'timestamp' in complete_data}")
    print(f"  • 包含 subgraphs: {'subgraphs' in complete_data}")
    print(f"  • 子图数量匹配: {len(complete_data['subgraphs']) == complete_data['total_subgraphs']}")
    print()
    
    # 验证每个子图的数据完整性
    all_valid = True
    for subgraph_id, subgraph_info in complete_data["subgraphs"].items():
        has_file_name = "file_name" in subgraph_info
        has_meta_data = "meta_data" in subgraph_info
        has_operations = "operations" in subgraph_info
        
        if not (has_file_name and has_meta_data and has_operations):
            print(f"  ❌ 子图 {subgraph_id} 数据不完整")
            all_valid = False
    
    if all_valid:
        print(f"  ✅ 所有子图数据完整")
    
    print()
    print("=" * 80)

def extract_subgraph_id(subgraph_name: str) -> str:
    """提取子图短ID"""
    name = subgraph_name.replace(".json", "")
    parts = name.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return name

if __name__ == "__main__":
    test_save_format()
