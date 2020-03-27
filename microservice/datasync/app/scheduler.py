from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.process import process
import os
def startSchedule():
    # Scheduler which will run at interval of once per day to sync all data
    checkin_score_scheduler = BackgroundScheduler()
    checkin_score_scheduler.add_job(process, trigger='interval', hours=1) #*2.5
    # sched.add_job(job_function, 'cron', day_of_week='mon-fri', hour=5, minute=30, end_date='2014-05-30')

    # checkin_score_scheduler.add_job(process, trigger='cron', day_of_week='mon-sun', hour=5, seconds=os.environ.get()) #*2.5
    # checkin_score_scheduler.add_job(process, CronTrigger.from_crontab(os.environ.get("CRON_SCHEDULE", '0 0 * * *')))

    # checkin_score_scheduler.start()
    # ideally code should work without this. because in case of large db. full sync is a problem


    # process() # this delays starting on flask as batch operation starts lock due to redis, lock removed now
