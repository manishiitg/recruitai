from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.process import process

def startSchedule():
    # Scheduler which will run at interval of once per day to sync all data
    checkin_score_scheduler = BackgroundScheduler()
    # checkin_score_scheduler.add_job(process_resumes, trigger='interval', seconds=os.getenv()) #*2.5
    # sched.add_job(job_function, 'cron', day_of_week='mon-fri', hour=5, minute=30, end_date='2014-05-30')

    # checkin_score_scheduler.add_job(process, trigger='cron', day_of_week='mon-sun', hour=5, seconds=os.getenv()) #*2.5
    checkin_score_scheduler.add_job(job_function, CronTrigger.from_crontab(os.getenv("CRON_SCHEDULE", '0 0 * * *')))

    checkin_score_scheduler.start()
    process() # this delays starting on flask as batch operation starts lock due to redis, lock removed now
