import os

from flask import Flask, make_response, jsonify

from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import BATCH_PROCESSING_DELAY

from app import token

jwt = token.init_token()

from app.scheduler import process_resumes

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping()

    CORS(app)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.errorhandler(400)
    def not_found(error):
        return make_response(jsonify(error='Not found'), 400)

    @app.errorhandler(500)
    def error_500(error):
        return make_response({}, 500)

    token.get_token(jwt=jwt, app=app)

    from app.api import auth
    from app.api import skill
    from app.api import emailclassify
    from app.api import resume
    from app.api import search
    from app.api import skillextract
    from app.api import datasync
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(skill.bp)
    app.register_blueprint(emailclassify.bp)
    app.register_blueprint(resume.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(skillextract.bp)
    app.register_blueprint(datasync.bp)
    
    
    # Scheduler which will run at interval of 60 seconds for user checkin score
    # checkin_score_scheduler = BackgroundScheduler()
    # checkin_score_scheduler.add_job(process_resumes, trigger='interval', seconds=BATCH_PROCESSING_DELAY) #*2.5
    # checkin_score_scheduler.start()
    # process_resumes() # this delays starting on flask as batch operation starts lock due to redis, lock removed now

    try:
        print("create app..")
        return app
    except Exception as e:
        print(e)
        # checkin_score_scheduler.shutdown()
        
