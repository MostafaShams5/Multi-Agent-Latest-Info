from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from config import REDIS_HOST, REDIS_PORT

jobstores = {
    'default': RedisJobStore(host=REDIS_HOST, port=REDIS_PORT, db=0)
}

# The scheduler instance that will be imported across the app
scheduler = AsyncIOScheduler(jobstores=jobstores)
