from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router import chat_rt
from router import history_rt
from service.sqlite import init_db

app = FastAPI()

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

app.include_router(chat_rt.router)
app.include_router(history_rt.router)

if __name__=='__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10081)
    