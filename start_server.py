"""
启动服务器脚本
"""
import uvicorn
from config import Config

if __name__ == "__main__":
    config = Config()
    uvicorn.run(
        "app:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )

