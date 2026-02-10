"""
API Gateway - 主入口
负责人：人员B2
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="模具成本核算系统 API",
    version="1.0.0",
    description="基于AI Agent的模具成本核算系统"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from api_gateway.routers import features, pricing, jobs, reports

app.include_router(features.router)
app.include_router(pricing.router)
app.include_router(jobs.router)
app.include_router(reports.router)

@app.get("/")
async def root():
    return {
        "message": "Mold Cost System API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "jobs": "/api/v1/jobs",
            "features": "/api/features",
            "pricing": "/api/pricing",
            "reports": "/api/v1/reports",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
