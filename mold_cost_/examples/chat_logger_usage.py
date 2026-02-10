"""
聊天日志使用示例
展示如何在不同的 Router 中使用聊天日志功能
"""

# ========== 示例1：在 review_router.py 中使用 ==========

from api_gateway.utils.chat_logger import (
    ensure_session_exists,
    log_system_message,
    log_user_message,
    log_assistant_message
)

# 在启动审核时
@router.post("/start")
async def start_review(
    request: ReviewStartRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """启动审核"""
    job_id = request.job_id
    user_id = current_user["user_id"]
    
    # 1. 确保会话存在
    await ensure_session_exists(
        db,
        session_id=job_id,
        job_id=job_id,
        user_id=user_id,
        metadata={"file_name": request.file_name}  # 可选
    )
    
    # 2. 调用 Agent 启动审核
    agent = InteractionAgent()
    result = await agent.start_review(job_id, db)
    
    # 3. 记录系统消息
    if result.status == "ok":
        await log_system_message(
            db,
            session_id=job_id,
            content=f"审核已启动，共查询到 {result.data['subgraphs_count']} 条数据",
            metadata={"action": "start_review", "data": result.data}
        )
    
    return result


# 在处理修改时
@router.post("/{job_id}/modify")
async def modify_review(
    job_id: str,
    request: ModifyRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """处理修改"""
    user_id = current_user["user_id"]
    
    # 1. 记录用户消息
    await log_user_message(
        db,
        session_id=job_id,
        content=request.modification_text,
        metadata={"user_id": user_id}
    )
    
    # 2. 调用 Agent 处理修改
    agent = InteractionAgent()
    result = await agent.handle_modification(
        job_id,
        request.modification_text,
        user_id
    )
    
    # 3. 记录助手回复
    if result.status == "ok":
        await log_assistant_message(
            db,
            session_id=job_id,
            content="修改已应用，请确认",
            metadata={
                "parsed_changes": result.data["parsed_changes"],
                "action": "modify"
            }
        )
    else:
        await log_assistant_message(
            db,
            session_id=job_id,
            content=f"修改失败：{result.message}",
            metadata={"error": result.message}
        )
    
    return result


# 在确认修改时
@router.post("/{job_id}/confirm")
async def confirm_review(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """确认修改"""
    user_id = current_user["user_id"]
    
    # 1. 调用 Agent 确认修改
    agent = InteractionAgent()
    result = await agent.confirm_changes(job_id, user_id, db)
    
    # 2. 记录系统消息
    if result.status == "ok":
        await log_system_message(
            db,
            session_id=job_id,
            content=f"修改已确认并保存，共 {result.data['modifications_count']} 处修改",
            metadata={"action": "confirm", "data": result.data}
        )
    
    return result


# ========== 示例2：在 chat_router.py 中使用 ==========

@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """SSE 聊天"""
    job_id = request.job_id
    user_id = current_user["user_id"]
    
    # 1. 确保会话存在
    await ensure_session_exists(
        db,
        session_id=job_id,
        job_id=job_id,
        user_id=user_id
    )
    
    # 2. 记录用户消息
    await log_user_message(
        db,
        session_id=job_id,
        content=request.message,
        metadata={"user_id": user_id}
    )
    
    # 3. 调用 Agent 生成回复
    agent = InteractionAgent()
    
    if request.stream:
        # 流式响应
        async def generate():
            full_response = ""
            
            async for chunk in agent.chat_stream(
                job_id,
                request.message,
                request.history or [],
                {}  # current_data
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'delta': chunk})}\n\n"
            
            # 4. 记录完整的助手回复
            await log_assistant_message(
                db,
                session_id=job_id,
                content=full_response,
                metadata={"stream": True}
            )
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    else:
        # 非流式响应
        response = await agent.chat(
            job_id,
            request.message,
            request.history or [],
            {}  # current_data
        )
        
        # 4. 记录助手回复
        await log_assistant_message(
            db,
            session_id=job_id,
            content=response,
            metadata={"stream": False}
        )
        
        return {"response": response}


# ========== 示例3：批量记录多条消息 ==========

async def log_conversation(
    db_session,
    session_id: str,
    messages: list
):
    """批量记录对话"""
    for msg in messages:
        if msg["role"] == "user":
            await log_user_message(
                db_session,
                session_id,
                msg["content"],
                msg.get("metadata")
            )
        elif msg["role"] == "assistant":
            await log_assistant_message(
                db_session,
                session_id,
                msg["content"],
                msg.get("metadata")
            )
        elif msg["role"] == "system":
            await log_system_message(
                db_session,
                session_id,
                msg["content"],
                msg.get("metadata")
            )


# ========== 示例4：错误处理 ==========

@router.post("/some-endpoint")
async def some_endpoint(db=Depends(get_db)):
    """带错误处理的示例"""
    try:
        # 业务逻辑
        result = await do_something()
        
        # 记录成功消息
        await log_system_message(
            db,
            session_id="xxx",
            content="操作成功"
        )
        
        return result
    
    except Exception as e:
        # 记录错误消息
        await log_system_message(
            db,
            session_id="xxx",
            content=f"操作失败：{str(e)}",
            metadata={"error": str(e), "error_type": type(e).__name__}
        )
        
        raise
