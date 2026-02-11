#!/bin/bash
# ============================================================================
# MCP 服务启动脚本 (Linux/macOS)
# 功能：启动 CAD Price Search MCP 服务（端口 8200）
# ============================================================================

echo ""
echo "========================================"
echo "  启动 MCP 服务"
echo "========================================"
echo ""

cd "$(dirname "$0")"
cd cad_price_search_mcp

echo "[INFO] 正在启动 CAD Price Search MCP 服务..."
echo "[INFO] 端口: 8200"
echo "[INFO] 按 Ctrl+C 停止服务"
echo ""

python server.py
