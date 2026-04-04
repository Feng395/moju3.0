"""
浠诲姟绠＄悊璺敱 (Controller灞?
澶勭悊HTTP璇锋眰鍜屽搷搴?璐熻矗浜猴細ZZH

鍚堝苟淇℃伅锛?- 鍚堝苟鏃ユ湡锛?026-02-10
- 婧愭枃浠讹細mold_cost_/api_gateway/routers/jobs.py + mold_cost-main/api_gateway/routers/jobs.py
- 鍚堝苟绛栫暐锛氫繚鐣?mold_cost_ 涓哄熀纭€锛岃ˉ鍏?mold_cost-main 鐨勯噸瑕佽矾鐢?- 涓昏鍔熻兘锛?  1. 鏂囦欢涓婁紶鍜屼换鍔″垱寤?(mold_cost_)
  2. 浠诲姟鐘舵€佹煡璇?(mold_cost_)
  3. 浠锋牸蹇収鏌ヨ (mold_cost_)
  4. 宸ヨ壓蹇収鏌ヨ (mold_cost_)
  5. 鏂囦欢涓嬭浇鍜岄绛惧悕URL鐢熸垚 (mold_cost_)
  6. 鑾峰彇浠诲姟璇︽儏锛堜娇鐢ㄨ鍥撅級(mold_cost-main)
  7. 浠诲姟鍒楄〃鏌ヨ (mold_cost-main)
  8. 缁х画鎵ц浠诲姟锛堝紓姝ュ悗鍙帮級(mold_cost-main)
- 璺敱绔偣锛?  - POST /jobs/upload - 涓婁紶鏂囦欢鍒涘缓浠诲姟 (mold_cost_)
  - POST /jobs/ - 鍒涘缓浠诲姟锛堟爣鍑哛EST椋庢牸锛?mold_cost-main)
  - GET /jobs/{job_id}/status - 鏌ヨ浠诲姟鐘舵€?(mold_cost_)
  - GET /jobs/{job_id}/snapshots/prices - 鏌ヨ浠锋牸蹇収 (mold_cost_)
  - GET /jobs/{job_id}/snapshots/processes - 鏌ヨ宸ヨ壓蹇収 (mold_cost_)
  - GET /jobs/{job_id}/files/{file_type}/download - 涓嬭浇鏂囦欢 (mold_cost_)
  - GET /jobs/{job_id}/files/{file_type}/url - 鑾峰彇棰勭鍚峌RL (mold_cost_)
  - GET /jobs/{job_id} - 鑾峰彇浠诲姟璇︽儏锛堜娇鐢ㄨ鍥撅級(mold_cost-main)
  - GET /jobs/ - 鑾峰彇浠诲姟鍒楄〃 (mold_cost-main)
  - POST /jobs/{job_id}/continue - 缁х画鎵ц浠诲姟 (mold_cost-main)
"""
from shared.unified_logging import get_logger
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import io

from shared.database import get_db
from ..auth import get_current_user
from ..services.job_service import JobService
from ..services.file_service import FileService
from mold_cost.application.use_cases.continue_job import ContinueJobUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# 鍏煎鏃х増鏈矾鐢憋紙涓嶅甫鍓嶇紑锛岀敤浜庡悜鍚庡吋瀹癸級
router_legacy = APIRouter(prefix="/api/jobs", tags=["jobs-legacy"])


@router.post("/upload")
async def upload_files(
    dwg_file: Optional[UploadFile] = File(None),
    prt_file: Optional[UploadFile] = File(None),
    encryption_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    涓婁紶DWG/PRT鏂囦欢骞跺垱寤轰换鍔?    
    Args:
        dwg_file: DWG鏂囦欢锛堝彲閫夛紝浣嗚嚦灏戣鏈変竴涓枃浠讹級
        prt_file: PRT鏂囦欢锛堝彲閫夛級
        encryption_key: 鍔犲瘑瀵嗛挜锛堥鐣欙紝绗竴鏈熶笉浣跨敤锛?        current_user: 褰撳墠鐢ㄦ埛锛堜粠JWT鑾峰彇锛?        db: 鏁版嵁搴撲細璇?    
    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "鏂囦欢涓婁紶鎴愬姛锛屼换鍔″凡鍒涘缓"
        }
    """
    try:
        job_service = JobService()
        
        result = await job_service.create_job_from_upload(
            db=db,
            user_id=current_user["user_id"],
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=encryption_key
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鏂囦欢涓婁紶寮傚父: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"鏈嶅姟鍣ㄥ唴閮ㄩ敊璇? {str(e)}"
            }
        )


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鏌ヨ浠诲姟鐘舵€?    
    Args:
        job_id: 浠诲姟ID
        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        浠诲姟鐘舵€佷俊鎭?    """
    try:
        job_service = JobService()
        
        result = await job_service.get_job_status(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鏌ヨ浠诲姟鐘舵€佸け璐? {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"鏌ヨ澶辫触: {str(e)}"
            }
        )


@router.get("/{job_id}/snapshots/prices")
async def get_job_price_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鏌ヨ浠诲姟鐨勪环鏍煎揩鐓?    
    Args:
        job_id: 浠诲姟ID
        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        浠锋牸蹇収鍒楄〃
    """
    try:
        job_service = JobService()
        
        result = await job_service.get_price_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鏌ヨ浠锋牸蹇収澶辫触: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )


@router.get("/{job_id}/snapshots/processes")
async def get_job_process_snapshots(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鏌ヨ浠诲姟鐨勫伐鑹鸿鍒欏揩鐓?    
    Args:
        job_id: 浠诲姟ID
        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        宸ヨ壓瑙勫垯蹇収鍒楄〃
    """
    try:
        job_service = JobService()
        
        result = await job_service.get_process_snapshots(
            db=db,
            job_id=job_id,
            user_id=current_user["user_id"]
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鏌ヨ宸ヨ壓瑙勫垯蹇収澶辫触: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )



@router.get("/{job_id}/files/{file_type}/download")
async def download_job_file(
    job_id: str,
    file_type: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    涓嬭浇浠诲姟鏂囦欢
    
    Args:
        job_id: 浠诲姟ID
        file_type: 鏂囦欢绫诲瀷 ("dwg" 鎴?"prt")
        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        鏂囦欢娴?    """
    try:
        file_service = FileService()
        
        # 鑾峰彇鏂囦欢鍐呭
        file_content = await file_service.get_job_file(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"]
        )
        
        # 纭畾鏂囦欢鎵╁睍鍚嶅拰MIME绫诲瀷
        if file_type.lower() == "dwg":
            media_type = "application/acad"
            extension = "dwg"
        elif file_type.lower() == "prt":
            media_type = "application/octet-stream"
            extension = "prt"
        else:
            raise HTTPException(400, detail="Invalid file type")
        
        # 返回文件流
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={job_id}.{extension}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鏂囦欢涓嬭浇澶辫触: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DOWNLOAD_FAILED", "message": str(e)}
        )


@router.get("/{job_id}/files/{file_type}/url")
async def get_job_file_url(
    job_id: str,
    file_type: str,
    expires_hours: int = 24,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鑾峰彇浠诲姟鏂囦欢鐨勯绛惧悕涓嬭浇URL
    
    Args:
        job_id: 浠诲姟ID
        file_type: 鏂囦欢绫诲瀷 ("dwg" 鎴?"prt")
        expires_hours: URL杩囨湡鏃堕棿锛堝皬鏃讹紝榛樿24灏忔椂锛?        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        {
            "url": "棰勭鍚峌RL",
            "expires_in": 86400,
            "file_type": "dwg"
        }
    """
    try:
        file_service = FileService()
        
        url = await file_service.get_job_file_url(
            db=db,
            job_id=job_id,
            file_type=file_type.lower(),
            user_id=current_user["user_id"],
            expires_hours=expires_hours
        )
        
        return {
            "url": url,
            "expires_in": expires_hours * 3600,
            "file_type": file_type.lower()
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鑾峰彇鏂囦欢URL澶辫触: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "URL_GENERATION_FAILED", "message": str(e)}
        )



# 馃啎 琛ュ厖鏉ヨ嚜 mold_cost-main 鐨勮矾鐢?
async def _execute_continue_job(orchestrator, job_id: Optional[str] = None):
    """
    鍚庡彴鎵ц浠诲姟缁х画娴佺▼
    
    Args:
        orchestrator: 鍏煎鏃ц皟鐢ㄧ鍚嶇殑鍗犱綅鍙傛暟
        job_id: 浠诲姟ID
    """
    try:
        if job_id is None:
            job_id = orchestrator
        logger.info(f"[鍚庡彴浠诲姟] 寮€濮嬬户缁墽琛屼换鍔? job_id={job_id}")

        await ContinueJobUseCase()._execute_continue_job(job_id)
        
    except Exception as e:
        logger.error(f"[鍚庡彴浠诲姟] 缁х画鎵ц寮傚父: job_id={job_id}, error={e}", exc_info=True)
        
        # 鍙戝竷澶辫触娑堟伅
        try:
            from shared.progress_publisher import ProgressPublisher
            from shared.progress_stages import ProgressStage, ProgressPercent
            
            progress_publisher = ProgressPublisher()
            progress_publisher.publish_progress(
                job_id=job_id,
                stage=ProgressStage.FAILED,
                progress=0,
                message=f"浠诲姟鎵ц澶辫触: {str(e)}",
                details={"source": "jobs_api", "error": str(e)}
            )
        except Exception as pub_error:
            logger.error(f"[鍚庡彴浠诲姟] 鍙戝竷澶辫触娑堟伅鏃跺嚭閿? {pub_error}", exc_info=True)


@router.get("/{job_id}")
@router_legacy.get("/{job_id}")
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鑾峰彇浠诲姟璇︽儏锛堜娇鐢ㄨ鍥剧‘淇濇暟鎹竴鑷存€э級
    
    鏉ヨ嚜 mold_cost-main锛屼娇鐢?v_job_cost_summary 瑙嗗浘
    """
    try:
        from sqlalchemy import text
        
        # 浣跨敤瑙嗗浘鏌ヨ锛岀‘淇?total_cost 濮嬬粓鍑嗙‘
        query = text("""
            SELECT 
                job_id,
                dwg_file_name,
                prt_file_name,
                status,
                progress,
                current_stage,
                total_cost,
                total_subgraphs as subgraph_count,
                material_cost,
                heat_treatment_cost,
                processing_cost_total,
                nc_cost,
                grinding_cost,
                wire_cost,
                error_message,
                created_at,
                updated_at,
                metadata
            FROM v_job_cost_summary
            WHERE job_id = :job_id
        """)
        
        result = await db.execute(query, {"job_id": job_id})
        row = result.mappings().fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"浠诲姟涓嶅瓨鍦? {job_id}")
        
        return {
            "job_id": str(row['job_id']),
            "dwg_file_name": row['dwg_file_name'],
            "prt_file_name": row['prt_file_name'],
            "status": row['status'],
            "progress": row['progress'],
            "current_stage": row['current_stage'],
            "total_cost": float(row['total_cost']) if row['total_cost'] else 0.0,
            "subgraph_count": row['subgraph_count'],
            "material_cost": float(row['material_cost']) if row['material_cost'] else 0.0,
            "heat_treatment_cost": float(row['heat_treatment_cost']) if row['heat_treatment_cost'] else 0.0,
            "processing_cost_total": float(row['processing_cost_total']) if row['processing_cost_total'] else 0.0,
            "nc_cost": float(row['nc_cost']) if row['nc_cost'] else 0.0,
            "grinding_cost": float(row['grinding_cost']) if row['grinding_cost'] else 0.0,
            "wire_cost": float(row['wire_cost']) if row['wire_cost'] else 0.0,
            "error_message": row['error_message'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
            "metadata": row['metadata']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"鑾峰彇浠诲姟璇︽儏澶辫触: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"鑾峰彇浠诲姟璇︽儏澶辫触: {str(e)}")


@router.get("/")
@router_legacy.get("/")
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    鑾峰彇浠诲姟鍒楄〃
    
    鏉ヨ嚜 mold_cost-main
    """
    # TODO: 瀹炵幇浠诲姟鍒楄〃鏌ヨ
    return {"jobs": [], "total": 0}


@router.post("/")
@router_legacy.post("/")
async def create_job(
    dwg_file: UploadFile = File(...),
    prt_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 中文注释：这里仍保留旧 REST 入口，但实现已经下沉到 JobService/use case。
    """
    鍒涘缓鏂颁换鍔★紙鏍囧噯REST椋庢牸锛?    
    鏉ヨ嚜 mold_cost-main锛屼笌 /upload 鍔熻兘鐩稿悓锛屾彁渚涙爣鍑哛EST API
    
    Args:
        dwg_file: DWG鏂囦欢锛堝繀椤伙級
        prt_file: PRT鏂囦欢锛堝彲閫夛級
        current_user: 褰撳墠鐢ㄦ埛
        db: 鏁版嵁搴撲細璇?    
    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "浠诲姟鍒涘缓鎴愬姛"
        }
    """
    try:
        job_service = JobService()
        
        result = await job_service.create_job_from_upload(
            db=db,
            user_id=current_user["user_id"],
            dwg_file=dwg_file,
            prt_file=prt_file,
            encryption_key=None
        )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"鉂?鍒涘缓浠诲姟澶辫触: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": f"鍒涘缓浠诲姟澶辫触: {str(e)}"
            }
        )


@router.post("/{job_id}/continue")
@router_legacy.post("/{job_id}/continue")
async def continue_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    鐢ㄦ埛纭鐗瑰緛璇嗗埆缁撴灉鍚庯紝缁х画鎵ц鍚庣画娴佺▼锛堝紓姝ュ悗鍙颁换鍔★級
    
    鏉ヨ嚜 mold_cost-main
    
    瑙﹀彂鏉′欢锛?    - 浠诲姟鐘舵€佷负 waiting_for_confirmation
    - 鐢ㄦ埛鍦ㄥ墠绔鏌ョ壒寰佽瘑鍒粨鏋滄棤璇悗锛岀偣鍑?寮€濮嬭绠椾环鏍?鎸夐挳
    
    鎵ц鍐呭锛?    - 宸ヨ壓鍐崇瓥锛堝鏋滈厤缃級
    - 浠锋牸璁＄畻
    - 瀹屾垚浠诲姟
    
    绔嬪嵆杩斿洖锛屽鐞嗗湪鍚庡彴鎵ц锛岄€氳繃 WebSocket 鎺ㄩ€佽繘搴?    
    Args:
        job_id: 浠诲姟ID
    
    Returns:
        {
            "status": "accepted",
            "message": "浠诲姟宸叉彁浜わ紝璇烽€氳繃 WebSocket 鐩戝惉杩涘害",
            "job_id": "xxx"
        }
    
    绀轰緥:
        ```bash
        curl -X POST http://localhost:8211/jobs/{job_id}/continue
        ```
    """
    try:
        import asyncio
        logger.info(f"鏀跺埌缁х画鎵ц璇锋眰: job_id={job_id}")
        
        # 瀵煎叆 Orchestrator
        orchestrator = None
        
        # 鑾峰彇 Orchestrator 瀹炰緥
        
        # 中文注释：继续执行在后台协程中推进。
        asyncio.create_task(_execute_continue_job(orchestrator, job_id))
        
        logger.info(f"浠诲姟宸叉彁浜ゅ埌鍚庡彴: job_id={job_id}")
        
        # 绔嬪嵆杩斿洖
        return {
            "status": "accepted",
            "message": "浠诲姟宸叉彁浜わ紝璇烽€氳繃 WebSocket 鐩戝惉杩涘害",
            "job_id": job_id
        }
        
    except Exception as e:
        logger.error(f"鎻愪氦浠诲姟澶辫触: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"鎻愪氦浠诲姟澶辫触: {str(e)}")





